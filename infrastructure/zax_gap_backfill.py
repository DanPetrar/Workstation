#!/usr/bin/env python3
"""Recovery half of the gap-tracking pair (see zax_gap_watch.py + Doc/gap-recovery-plan.md,
ZaxModbus repo).

Every 15 min (cron): for each open/partial data_gap point, check whether the
unit's live delivery has resumed; if so, pull the gap range from the device's
own /api/export (same LAN, no relay needed), diff against what's already in
Influx, backfill the missing seconds (source=buffer_backfill), and rewrite the
data_gap point to status=recovered/partial. Idempotent -- safe to re-run.

2026-08-05 incident: a gap that never reached the 95% recovered threshold
stayed "partial" and got re-picked-up every single cron run, forever, with
`start_ts` never advancing while `hi` (live position) kept moving forward --
one gap's requested /api/export range grew to 9 days old. The device's export
handler walks its whole ring per call (no early exit on an out-of-range ts),
so that pull stalled Unit_A's main loop -- and therefore its box-serial read
-- for 45-134s per attempt, misread as recurring "box comm lost" faults.
Fixed here: MAX_GAP_AGE_S closes out ancient gaps instead of retrying forever,
MAX_PULL_WINDOW_S bounds how much each pull asks for, a flock keeps cron runs
from piling up if one run stalls past the next scheduled one, and a broad
per-unit try/except stops one unit's failure from aborting the rest.
"""
import csv
import datetime
import fcntl
import io
import sys
import time
import urllib.request
from influxdb_client import InfluxDBClient, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

URL = "http://localhost:8086"
TOKEN = "ZQ7dEWGvC_N_GB4jSKDKWPN1F7S2R_2GWrY_WPGoJZip_tJEF9gOjN8o3HVItsmHoYoQ_Y40nammeb1T4fQkyQ=="
ORG = "zax"
BUCKET = "zaxenergy"
STALE_S = 180            # must match zax_gap_watch.py's threshold
MAX_GAP_AGE_S = 6 * 3600   # give up retrying a gap older than this -- close it
                           # out (best-effort "recovered") instead of leaving
                           # it "partial" to be re-pulled every 15 min forever
MAX_PULL_WINDOW_S = 3600   # width of ONE recovery window
MAX_WINDOWS_PER_RUN = 8    # 8 x 3600 s = 8 h, comfortably past the ~6.2 h ring, so a
                           # gap inside the ring's capacity is fully walked in one run
                           # rather than having its tail pulled and the rest declared
                           # recovered (the pre-2026-09-01 behaviour: `expected` was
                           # computed from the CLAMPED window, so any gap over an hour
                           # was stamped "recovered" after one window's worth of fill —
                           # silent loss, with no "partial" ever shown)
LOCK_PATH = "/tmp/zax_gap_backfill.lock"

DEVICE_IPS = {
    "Unit_A": "192.168.20.231",
    "Unit_B": "192.168.20.232",
    "Unit_C": "192.168.20.233",
    "Unit_D": "192.168.20.234",
}

cli = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
qapi = cli.query_api()
wapi = cli.write_api(write_options=SYNCHRONOUS)


def open_gaps():
    """Return [(unit, stream, start_ts)].

    `stream` MUST be carried through and written back verbatim. InfluxDB series
    identity is measurement + FULL tag set, so `data_gap,unit=X,stream=sec` and
    `data_gap,unit=X` are different series — a status write that omits the tag
    lands in a phantom series, the real point stays "open" forever, and this
    function re-selects it every run. That is the 2026-08-05 runaway-cron shape,
    and it was live for a few hours on 2026-09-01 when the detector gained the
    tag and this writer did not.

    Points written before the tag existed have stream=None and must be written
    back WITHOUT the tag, or the fix creates the same split it repairs."""
    q = (f'from(bucket:"{BUCKET}") |> range(start:-30d) '
         f'|> filter(fn:(r)=> r._measurement=="data_gap") '
         f'|> filter(fn:(r)=> r._field=="status") '
         # TERMINAL statuses, both excluded: "recovered" (the data is present)
         # and "unrecoverable" (we asked for the whole span and the ring no
         # longer had it). Only "open" and "partial" are re-selected — a
         # terminal status that stayed selectable would retry forever, which is
         # the 2026-08-05 failure mode.
         f'|> filter(fn:(r)=> r._value != "recovered" and r._value != "unrecoverable") '
         f'|> sort(columns:["_time"])')
    out = []
    for table in qapi.query(q):
        for rec in table.records:
            out.append((rec.values.get("unit"), rec.values.get("stream"),
                        int(rec.get_time().timestamp())))
    return out


def last_seen(unit):
    q = (f'from(bucket:"{BUCKET}") |> range(start:-30d) '
         f'|> filter(fn:(r)=> r._measurement=="power" and r.unit=="{unit}" and r._field=="v") '
         f'|> group() |> last()')
    tables = qapi.query(q)
    if not tables or not tables[0].records:
        return None
    return int(tables[0].records[0].get_time().timestamp())


def existing_influx_seconds(unit, lo, hi):
    q = (f'from(bucket:"{BUCKET}") |> range(start:{lo-1}, stop:{hi+1}) '
         f'|> filter(fn:(r)=> r._measurement=="power" and r.unit=="{unit}" and r._field=="v") '
         f'|> group()')
    seen = set()
    for table in qapi.query(q):
        for rec in table.records:
            seen.add(int(rec.get_time().timestamp()))
    return seen


# A single /api/export call blocks the device's loop() for the whole response,
# and loop() is also what reads the box serial line. Measured 2026-09-01 on
# Unit_A (fw 1.1.28): a 1 h window = 2,081 rows = 15.8 s of response time, during
# which /api/data latency hit 15.29 s and the unit logged TWO "Box comm lost -- no
# data for 10s" faults, each with "restored" in the same second -- the signature
# of a frozen loop(), not a real outage.
#
# The 2026-08-05 incident was the same mechanism at 45-134 s. Firmware v1.1.19's
# early-exit bounded the SCAN, but not this: cost is per EMITTED row, so a large
# window still stalls the unit past the 10 s comm-loss threshold.
#
# So pull in chunks. Separate HTTP requests let loop() run -- and therefore the
# box parser -- in between, keeping every individual stall well under the
# threshold. ~7.6 ms/row measured, so 240 rows is ~1.8 s.
CHUNK_S = 240          # seconds of ring per request (~240 rows, ~1.8 s stall)
CHUNK_PAUSE_S = 0.5    # let the device drain its box backlog between chunks


def _pull_csv(unit, kind, lo, hi):
    """-> (rows, next_from). next_from is set when the device truncated the
    window at EXPORT_MAX_ROWS and there is more to fetch from that timestamp."""
    url = f"http://{DEVICE_IPS[unit]}/api/export?type={kind}&from={lo}&to={hi}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        rows = list(csv.DictReader(io.StringIO(resp.read().decode())))
        nf = resp.headers.get("X-Zax-Next-From")
    return rows, (int(nf) if nf else None)


def _pull_chunked(unit, kind, lo, hi):
    """Walk [lo, hi] in CHUNK_S slices so no single request stalls the device
    past its comm-loss threshold. Returns {ts: row}.

    Follows X-Zax-Next-From (fw v1.1.30+) rather than assuming a slice fits in
    one response. /api/export caps a reply at EXPORT_MAX_ROWS = 400 and reports
    where to resume; CHUNK_S = 240 stays under that only because sec records are
    1 Hz, so the cap was never hit and the header never read. Any change to
    CHUNK_S, a denser cadence, or a min-record walk would silently have lost
    every row past the 400th. Verified live 2026-09-03: a 700 s window returns
    exactly 400 rows plus a next_from.
    """
    out = {}
    start = lo
    while start <= hi:
        end = min(start + CHUNK_S - 1, hi)
        cursor = start
        while cursor is not None and cursor <= end:
            rows, nf = _pull_csv(unit, kind, cursor, end)
            for r in rows:
                out[int(r["ts"])] = r
            if nf is None or not rows:
                break
            if nf <= cursor:          # device would not advance — stop rather than spin
                break
            cursor = nf
            time.sleep(CHUNK_PAUSE_S)
        start = end + 1
        if start <= hi:
            time.sleep(CHUNK_PAUSE_S)
    return out


def pull_ring(unit, lo, hi):
    return _pull_chunked(unit, "sec", lo, hi)


def write_gap(unit, start_ts, status, duration_s, recovered_count, stream=None):
    """Rewrite the gap point IN PLACE. `stream` must match what the detector
    wrote (or be None for pre-tag points) — see open_gaps()."""
    now = int(datetime.datetime.now().timestamp())
    tags = f"unit={unit}" + (f",stream={stream}" if stream else "")
    line = (f'data_gap,{tags} '
            f'end_ts={now}i,duration_s={duration_s},status="{status}",'
            f'recovered_at={now}i,recovered_count={recovered_count}i,source="watermark_cron" '
            f'{start_ts * 1_000_000_000}')
    wapi.write(bucket=BUCKET, org=ORG, record=line, write_precision=WritePrecision.NS)


def backfill_points(unit, ring_by_ts, missing_ts):
    """Write recovered seconds as `power` points.

    var/pf are emitted when the device's CSV carries them. Until fw v1.1.28
    /api/export shipped only v,a,w,hz -- 4 of the 6 quantities the ring holds --
    so a recovered second could never match a live one, which zax_parser writes
    with all six. Buffering exists to make recovery EQUIVALENT to live delivery;
    a lossy export defeats that. Columns are keyed by NAME, so this handles both
    the old and new CSV without a version check.
    """
    lines = []
    for ts in missing_ts:
        r = ring_by_ts[ts]
        for ph in ("r", "s", "t"):
            Ph = ph.upper()
            f = [f"v={r['v_'+ph]}", f"a={r['a_'+ph]}",
                 f"w={r['w_'+ph]}", f"hz={r['hz_'+ph]}"]
            if ("var_" + ph) in r:
                f.append(f"var={int(float(r['var_' + ph]))}i")   # int field, matches live
            if ("pf_" + ph) in r:
                f.append(f"pf={r['pf_' + ph]}")
            lines.append(f"power,unit={unit},phase={Ph},source=buffer_backfill "
                         + ",".join(f) + f" {ts}")
    for i in range(0, len(lines), 1500):
        wapi.write(bucket=BUCKET, org=ORG, record="\n".join(lines[i:i + 1500]),
                   write_precision=WritePrecision.S)


def pull_ring_min(unit, lo, hi):
    """MIN (energy) ring. /api/export has always supported type=min; this script
    only ever asked for sec, so energy gaps were never recovered at all.
    Chunked like the sec pull -- a wide window is still a wide window."""
    return _pull_chunked(unit, "min", lo, hi)


def existing_influx_energy(unit, lo, hi):
    q = (f'from(bucket:"{BUCKET}") |> range(start:{lo-1}, stop:{hi+1}) '
         f'|> filter(fn:(r)=> r._measurement=="energy" and r.unit=="{unit}" '
         f'and r._field=="kwh") |> group()')
    seen = set()
    for table in qapi.query(q):
        for rec in table.records:
            seen.add(int(rec.get_time().timestamp()))
    return seen


def backfill_energy(unit, lo, hi):
    """Recover the MIN ring for the same window. Best-effort and non-fatal: a
    failure here must not lose the sec recovery that already succeeded."""
    try:
        ring = pull_ring_min(unit, lo, hi)
    except Exception as e:
        print(f"{unit}: min export pull failed ({e}), energy not recovered")
        return 0
    missing = sorted(set(ring) - existing_influx_energy(unit, lo, hi))
    lines = []
    for ts in missing:
        r = ring[ts]
        for ph in ("r", "s", "t"):
            Ph = ph.upper()
            f = [f"kwh={r['kwh_'+ph]}", f"kvarh={r['kvarh_'+ph]}"]
            # v1.2.0 adds export counters. Written ONLY when the device reports
            # them -- absent must stay distinguishable from measured-as-zero.
            if ("kwh_exp_" + ph) in r:
                f.append(f"kwh_exp={r['kwh_exp_' + ph]}")
            if ("kvarh_exp_" + ph) in r:
                f.append(f"kvarh_exp={r['kvarh_exp_' + ph]}")
            lines.append(f"energy,unit={unit},phase={Ph},source=buffer_backfill "
                         + ",".join(f) + f" {ts}")
    for i in range(0, len(lines), 1500):
        wapi.write(bucket=BUCKET, org=ORG, record="\n".join(lines[i:i + 1500]),
                   write_precision=WritePrecision.S)
    return len(missing)


def main():
    now = int(datetime.datetime.now().timestamp())
    for unit, stream, start_ts in open_gaps():
        try:
            _process_gap(unit, start_ts, now, stream)
        except Exception as e:
            print(f"{unit}/{stream}: unhandled error processing gap at {start_ts} "
                  f"({e}), leaving it for the next run")


def _process_gap(unit, start_ts, now, stream=None):
    if now - start_ts > MAX_GAP_AGE_S:
        # Too old to keep retrying -- the ring holds ~6.2 h and this gap is
        # older than that, so the data is gone. Marked "unrecoverable", NOT
        # "recovered": those seconds were never retrieved and the record must
        # not claim they were. Terminal, so open_gaps() stops selecting it.
        write_gap(unit, start_ts, "unrecoverable", float(now - start_ts), 0, stream)
        print(f"{unit}/{stream}: gap at {start_ts} exceeded {MAX_GAP_AGE_S}s and the unit "
              f"never came back -> unrecoverable")
        return

    ts = last_seen(unit)
    if ts is None or now - ts > STALE_S:
        print(f"{unit}: still down since {start_ts}, skipping this round")
        return

    hi = ts  # live delivery resumed as of this timestamp
    print(f"{unit}/{stream}: live at {hi}, walking [{start_ts}, {hi}] "
          f"in {MAX_PULL_WINDOW_S}s windows")

    covered_to = start_ts
    windows = 0
    n_sec = n_min = 0
    while covered_to <= hi and windows < MAX_WINDOWS_PER_RUN:
        w_hi = min(covered_to + MAX_PULL_WINDOW_S - 1, hi)
        try:
            ring = pull_ring(unit, covered_to, w_hi)
        except Exception as e:
            print(f"{unit}: export pull failed at [{covered_to},{w_hi}] ({e}), "
                  f"leaving gap open for the next run")
            return
        missing = sorted(set(ring) - existing_influx_seconds(unit, covered_to, w_hi))
        if missing:
            backfill_points(unit, ring, missing)
            n_sec += len(missing)
        n_min += backfill_energy(unit, covered_to, w_hi)
        covered_to = w_hi + 1
        windows += 1

    asked_for_everything = covered_to > hi

    # Honest status. "recovered" is claimed ONLY when the seconds are actually
    # present in InfluxDB across the WHOLE gap -- not when one window happened
    # to fill. If the full span was requested and the data still is not there,
    # the ring had already wrapped past it and it is gone: say so.
    present = len(existing_influx_seconds(unit, start_ts, hi))
    expected = max(hi - start_ts, 1)
    if not asked_for_everything:
        status_out = "partial"          # more windows to walk on the next run
    elif present >= 0.95 * expected:
        status_out = "recovered"
    else:
        status_out = "unrecoverable"    # asked for all of it; the ring no longer had it

    write_gap(unit, start_ts, status_out, float(hi - start_ts), present, stream)
    print(f"{unit}/{stream}: {windows} window(s), +{n_sec} sec +{n_min} min, "
          f"{present}/{expected} present -> {status_out}")


if __name__ == "__main__":
    lockfile = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("zax_gap_backfill.py: previous run still in progress, skipping this cycle")
        sys.exit(0)
    try:
        main()
    finally:
        fcntl.flock(lockfile, fcntl.LOCK_UN)

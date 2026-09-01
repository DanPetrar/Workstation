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
MAX_PULL_WINDOW_S = 3600   # never ask a device for more than this much range
                           # in one call, regardless of how old start_ts is
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
    q = (f'from(bucket:"{BUCKET}") |> range(start:-30d) '
         f'|> filter(fn:(r)=> r._measurement=="data_gap") '
         f'|> filter(fn:(r)=> r._field=="status") '
         f'|> filter(fn:(r)=> r._value != "recovered") '
         f'|> group() |> sort(columns:["_time"])')
    out = []
    for table in qapi.query(q):
        for rec in table.records:
            out.append((rec.values.get("unit"), int(rec.get_time().timestamp())))
    return out  # [(unit, start_ts), ...]


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
    url = f"http://{DEVICE_IPS[unit]}/api/export?type={kind}&from={lo}&to={hi}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return list(csv.DictReader(io.StringIO(resp.read().decode())))


def _pull_chunked(unit, kind, lo, hi):
    """Walk [lo, hi] in CHUNK_S slices so no single request stalls the device
    past its comm-loss threshold. Returns {ts: row}."""
    out = {}
    start = lo
    while start <= hi:
        end = min(start + CHUNK_S - 1, hi)
        for r in _pull_csv(unit, kind, start, end):
            out[int(r["ts"])] = r
        start = end + 1
        if start <= hi:
            time.sleep(CHUNK_PAUSE_S)
    return out


def pull_ring(unit, lo, hi):
    return _pull_chunked(unit, "sec", lo, hi)


def write_gap(unit, start_ts, status, duration_s, recovered_count):
    now = int(datetime.datetime.now().timestamp())
    line = (f'data_gap,unit={unit} '
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
    for unit, start_ts in open_gaps():
        try:
            _process_gap(unit, start_ts, now)
        except Exception as e:
            print(f"{unit}: unhandled error processing gap at {start_ts} ({e}), "
                  f"leaving it for the next run")


def _process_gap(unit, start_ts, now):
    if now - start_ts > MAX_GAP_AGE_S:
        # Too old to keep retrying -- the ring almost certainly no longer
        # holds most of it anyway. Close it out so it stops being re-picked-up
        # every 15 min; whatever's still in the ring was already recovered by
        # an earlier run's partial pull (existing_influx_seconds dedupes).
        write_gap(unit, start_ts, "recovered", float(now - start_ts), 0)
        print(f"{unit}: gap at {start_ts} exceeded {MAX_GAP_AGE_S}s, closed out (best-effort)")
        return

    ts = last_seen(unit)
    if ts is None or now - ts > STALE_S:
        print(f"{unit}: still down since {start_ts}, skipping this round")
        return

    hi = ts  # live delivery resumed as of this timestamp
    lo = max(start_ts, hi - MAX_PULL_WINDOW_S)
    print(f"{unit}: recovered live at {hi}, pulling ring for [{lo}, {hi}]"
          + (f" (clamped from {start_ts})" if lo != start_ts else ""))
    try:
        ring_by_ts = pull_ring(unit, lo, hi)
    except Exception as e:
        print(f"{unit}: export pull failed ({e}), leaving gap open")
        return

    existing = existing_influx_seconds(unit, lo, hi)
    missing = sorted(set(ring_by_ts) - existing)
    if missing:
        backfill_points(unit, ring_by_ts, missing)

    # Energy (MIN ring) over the same window. Detection watches `power` only, so
    # an energy hole is invisible; recovering it alongside every sec recovery is
    # the cheap way to keep the two measurements consistent.
    n_min = backfill_energy(unit, lo, hi)
    if n_min:
        print(f"{unit}: wrote {n_min} backfilled energy minutes")

    expected = max(hi - lo, 1)
    recovered_count = len(ring_by_ts)
    # A window-clamped pull can never itself reach 95% of the ORIGINAL gap's
    # span, only of the clamped one -- status reflects this pull, not the
    # full original gap (MAX_GAP_AGE_S is what eventually closes the rest).
    status_out = "recovered" if recovered_count >= 0.95 * expected else "partial"
    write_gap(unit, start_ts, status_out, float(hi - start_ts), recovered_count)
    print(f"{unit}: wrote {len(missing)} backfilled seconds, gap marked {status_out}")


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

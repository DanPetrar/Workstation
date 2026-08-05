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


def pull_ring(unit, lo, hi):
    url = f"http://{DEVICE_IPS[unit]}/api/export?type=sec&from={lo}&to={hi}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        text = resp.read().decode()
    rows = list(csv.DictReader(io.StringIO(text)))
    return {int(r["ts"]): r for r in rows}


def write_gap(unit, start_ts, status, duration_s, recovered_count):
    now = int(datetime.datetime.now().timestamp())
    line = (f'data_gap,unit={unit} '
            f'end_ts={now}i,duration_s={duration_s},status="{status}",'
            f'recovered_at={now}i,recovered_count={recovered_count}i,source="watermark_cron" '
            f'{start_ts * 1_000_000_000}')
    wapi.write(bucket=BUCKET, org=ORG, record=line, write_precision=WritePrecision.NS)


def backfill_points(unit, ring_by_ts, missing_ts):
    lines = []
    for ts in missing_ts:
        r = ring_by_ts[ts]
        for ph in ("r", "s", "t"):
            Ph = ph.upper()
            lines.append(
                f"power,unit={unit},phase={Ph},source=buffer_backfill "
                f"v={r['v_'+ph]},a={r['a_'+ph]},w={r['w_'+ph]},hz={r['hz_'+ph]} {ts}"
            )
    for i in range(0, len(lines), 1500):
        wapi.write(bucket=BUCKET, org=ORG, record="\n".join(lines[i:i + 1500]),
                   write_precision=WritePrecision.S)


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

#!/usr/bin/env python3
"""Recovery half of the gap-tracking pair (see zax_gap_watch.py + Doc/gap-recovery-plan.md,
ZaxModbus repo).

Every 15 min (cron): for each open/partial data_gap point, check whether the
unit's live delivery has resumed; if so, pull the gap range from the device's
own /api/export (same LAN, no relay needed), diff against what's already in
Influx, backfill the missing seconds (source=buffer_backfill), and rewrite the
data_gap point to status=recovered/partial. Idempotent -- safe to re-run.
"""
import csv
import datetime
import io
import urllib.request
from influxdb_client import InfluxDBClient, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

URL = "http://localhost:8086"
TOKEN = "ZQ7dEWGvC_N_GB4jSKDKWPN1F7S2R_2GWrY_WPGoJZip_tJEF9gOjN8o3HVItsmHoYoQ_Y40nammeb1T4fQkyQ=="
ORG = "zax"
BUCKET = "zaxenergy"
STALE_S = 180  # must match zax_gap_watch.py's threshold

DEVICE_IPS = {
    "Unit_A": "192.168.20.102",
    "Unit_B": "192.168.20.113",
    "Unit_C": "192.168.20.103",
    "Unit_D": "192.168.20.105",
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
        ts = last_seen(unit)
        if ts is None or now - ts > STALE_S:
            print(f"{unit}: still down since {start_ts}, skipping this round")
            continue

        hi = ts  # live delivery resumed as of this timestamp
        print(f"{unit}: recovered live at {hi}, pulling ring for [{start_ts}, {hi}]")
        try:
            ring_by_ts = pull_ring(unit, start_ts, hi)
        except Exception as e:
            print(f"{unit}: export pull failed ({e}), leaving gap open")
            continue

        existing = existing_influx_seconds(unit, start_ts, hi)
        missing = sorted(set(ring_by_ts) - existing)
        if missing:
            backfill_points(unit, ring_by_ts, missing)

        expected = max(hi - start_ts, 1)
        recovered_count = len(ring_by_ts)
        status_out = "recovered" if recovered_count >= 0.95 * expected else "partial"
        write_gap(unit, start_ts, status_out, float(hi - start_ts), recovered_count)
        print(f"{unit}: wrote {len(missing)} backfilled seconds, gap marked {status_out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Watermark-based gap detector for the 4 bench ZaxEnergy units (Unit_A/B/C/D).

Every 5 min (cron): if a unit's most recent `power` point in InfluxDB is older
than STALE_S, write/update a `data_gap` point for it. The point is keyed by
(unit, start_ts) -- start_ts stays pinned to the last-known-good watermark for
as long as the gap continues, so re-running this during an ongoing outage
naturally rewrites the SAME point (updated duration_s) rather than creating
duplicates. See Doc/gap-recovery-plan.md (ZaxModbus repo) for the full design.
"""
import datetime
from influxdb_client import InfluxDBClient, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

URL = "http://localhost:8086"
TOKEN = "ZQ7dEWGvC_N_GB4jSKDKWPN1F7S2R_2GWrY_WPGoJZip_tJEF9gOjN8o3HVItsmHoYoQ_Y40nammeb1T4fQkyQ=="
ORG = "zax"
BUCKET = "zaxenergy"
UNITS = ["Unit_A", "Unit_B", "Unit_C", "Unit_D"]
STALE_S = 180  # normal cadence is ~1Hz; well above any single missed publish

cli = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
qapi = cli.query_api()
wapi = cli.write_api(write_options=SYNCHRONOUS)


def last_seen(unit):
    q = (f'from(bucket:"{BUCKET}") |> range(start:-30d) '
         f'|> filter(fn:(r)=> r._measurement=="power" and r.unit=="{unit}" and r._field=="v") '
         f'|> group() |> last()')
    tables = qapi.query(q)
    if not tables or not tables[0].records:
        return None
    return int(tables[0].records[0].get_time().timestamp())


def write_gap(unit, start_ts, duration_s):
    line = (f'data_gap,unit={unit} '
            f'end_ts=0i,duration_s={duration_s},status="open",'
            f'recovered_at=0i,recovered_count=0i,source="watermark_cron" '
            f'{start_ts * 1_000_000_000}')
    wapi.write(bucket=BUCKET, org=ORG, record=line, write_precision=WritePrecision.NS)


def main():
    now = int(datetime.datetime.now().timestamp())
    for unit in UNITS:
        ts = last_seen(unit)
        if ts is None:
            print(f"{unit}: no data ever seen, skipping")
            continue
        age = now - ts
        if age > STALE_S:
            write_gap(unit, ts, float(age))
            print(f"{unit}: STALE {age}s (since {datetime.datetime.fromtimestamp(ts)}) -> data_gap written")
        else:
            print(f"{unit}: OK ({age}s)")


if __name__ == "__main__":
    main()

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

# Energy (MIN) arrives once per MINUTE, not per second, so the sec threshold
# would false-positive on ordinary jitter. 5 missed minutes is the equivalent
# margin. Until 2026-09-01 this stream was not watched at all: an energy-only
# hole -- sec frames flowing while min frames are not, which the firmware's
# "a rejected W line must not close the set" rule makes a real case -- was
# invisible, and therefore never recovered either.
STALE_MIN_S = 300

# A device's `ts` is 0 until its clock is set, and a boot-relative watermark
# would key a data_gap point near epoch 0 -- where two unrelated outages can
# collide and silently overwrite each other's record. A gap we cannot key
# correctly is worse than no gap: it corrupts a neighbour's. Anything below this
# is not wall-clock and is refused rather than acted on. (The firmware hit the
# same class of bug from the other direction on 2026-08-05: arithmetic on a
# boot-relative ts wrapped to a bogus uint32 -- see _push's docstring in
# tools/zaxtest/cases/test_ts.py.)
SANE_EPOCH = 1_577_836_800   # 2020-01-01

cli = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
qapi = cli.query_api()
wapi = cli.write_api(write_options=SYNCHRONOUS)


def last_seen(unit, measurement="power", field="v"):
    q = (f'from(bucket:"{BUCKET}") |> range(start:-30d) '
         f'|> filter(fn:(r)=> r._measurement=="{measurement}" and r.unit=="{unit}" '
         f'and r._field=="{field}") |> group() |> last()')
    tables = qapi.query(q)
    if not tables or not tables[0].records:
        return None
    return int(tables[0].records[0].get_time().timestamp())


def write_gap(unit, start_ts, duration_s, stream="sec"):
    """`stream` distinguishes a power gap from an energy gap. Points written
    before 2026-09-01 carry no stream tag and remain their own series; the
    backfill does not filter on it (it recovers both rings for any gap), so the
    tag is for attribution, not routing."""
    line = (f'data_gap,unit={unit},stream={stream} '
            f'end_ts=0i,duration_s={duration_s},status="open",'
            f'recovered_at=0i,recovered_count=0i,source="watermark_cron" '
            f'{start_ts * 1_000_000_000}')
    wapi.write(bucket=BUCKET, org=ORG, record=line, write_precision=WritePrecision.NS)


def _check(unit, now, label, measurement, field, threshold, stream):
    ts = last_seen(unit, measurement, field)
    if ts is None:
        print(f"{unit}/{label}: no data ever seen, skipping")
        return
    if ts < SANE_EPOCH:
        print(f"{unit}/{label}: watermark {ts} is not wall-clock "
              f"(boot-relative?), refusing to key a gap on it")
        return
    age = now - ts
    if age > threshold:
        write_gap(unit, ts, float(age), stream)
        print(f"{unit}/{label}: STALE {age}s "
              f"(since {datetime.datetime.fromtimestamp(ts)}) -> data_gap written")
    else:
        print(f"{unit}/{label}: OK ({age}s)")


def main():
    now = int(datetime.datetime.now().timestamp())
    for unit in UNITS:
        _check(unit, now, "power",  "power",  "v",   STALE_S,     "sec")
        _check(unit, now, "energy", "energy", "kwh", STALE_MIN_S, "min")


if __name__ == "__main__":
    main()

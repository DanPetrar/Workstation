#!/usr/bin/env python3
"""One-time backfill: replay SQLite cal_data.db into InfluxDB for the window that
predates the cal-parser service (gap 2026-06-02 14:00 -> ~19:34 local).

Mirrors /opt/cal-parser/cal_parser.py exactly (same measurements/fields/tags,
ns timestamps). Idempotent: writing measurement+tagset+ts overwrites, never dupes.

Modes:
  --validate   compare SQLite-derived points vs existing Influx for one minute >= cutoff
  --apply      write all rows with ts < cutoff (the missing gap)
"""
import sqlite3, sys, datetime
from influxdb_client import InfluxDBClient, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

DB = "/workspace/cal-data/cal_data.db"
URL = "http://localhost:8086"
TOKEN = "ZQ7dEWGvC_N_GB4jSKDKWPN1F7S2R_2GWrY_WPGoJZip_tJEF9gOjN8o3HVItsmHoYoQ_Y40nammeb1T4fQkyQ=="
ORG = "zax"; BUCKET = "zaxenergy"; UNIT = "cal_F07F8C"; PHASES = ["R", "S", "T"]

cli = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
qapi = cli.query_api()
wapi = cli.write_api(write_options=SYNCHRONOUS)


def cutoff_ts():
    """Earliest existing Influx point across the backfilled measurements (epoch s)."""
    q = ('from(bucket:"zaxenergy") |> range(start:0) '
         '|> filter(fn:(r)=> r._measurement=="cal_box" and r._field=="dkwh") '
         '|> group() |> first()')
    t = qapi.query(q)[0].records[0].get_time()
    return int(t.timestamp())


def sec_points(row):
    d = dict(row)
    ts_ns = d["ts"] * 1_000_000_000
    out = []
    for p in PHASES:
        out.append(f"power,unit={UNIT},phase={p} "
                   f"v={d[p+'_v']},a={d[p+'_a']},w={d[p+'_w']},"
                   f"hz={d[p+'_hz']},pf={d[p+'_pf']} {ts_ns}")
    return out


def min_points(row):
    d = dict(row)
    ts_ns = d["ts"] * 1_000_000_000
    out = [f"cal_meter,unit={UNIT} "
           f"v={d['mtr_v']},a={d['mtr_a']},w={d['mtr_w']},"
           f"pf={d['mtr_pf']},hz={d['mtr_hz']},dkwh={d['mtr_dkwh']} {ts_ns}"]
    for p in PHASES:
        w, dk = d[p+'_w'], d[p+'_dkwh']
        if w is not None and dk is not None:
            out.append(f"cal_box,unit={UNIT},phase={p} w={w},dkwh={dk} {ts_ns}")
        wp, dkp = d[p+'_dev_w_pct'], d[p+'_dev_dkwh_pct']
        if wp is not None and dkp is not None:
            out.append(f"cal_dev,unit={UNIT},phase={p} w_pct={wp},dkwh_pct={dkp} {ts_ns}")
    return out


def validate(cut):
    """Pick a cal_min ts >= cutoff that's already in Influx; compare cal_box."""
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM cal_min WHERE ts>=? ORDER BY ts LIMIT 1", (cut,)).fetchone()
    ts = row["ts"]
    print(f"validate minute ts={ts} ({datetime.datetime.fromtimestamp(ts)})")
    print("  SQLite-derived cal_box:",
          {p: (row[p+'_w'], row[p+'_dkwh']) for p in PHASES})
    q = (f'from(bucket:"zaxenergy") |> range(start:{ts-1}, stop:{ts+1}) '
         f'|> filter(fn:(r)=> r._measurement=="cal_box") '
         f'|> pivot(rowKey:["_time","phase"], columnKey:["_field"], valueColumn:"_value")')
    inf = {}
    for tbl in qapi.query(q):
        for r in tbl.records:
            inf[r["phase"]] = (r.values.get("w"), r.values.get("dkwh"))
    print("  Influx stored   cal_box:", inf)
    ok = all(abs(row[p+'_w']-inf[p][0])<1e-6 and abs(row[p+'_dkwh']-inf[p][1])<1e-6
             for p in PHASES if p in inf)
    print("  MATCH" if ok and inf else "  MISMATCH/﻿missing — DO NOT APPLY")


def apply(cut):
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    lo = con.execute("SELECT MIN(ts) FROM cal_sec").fetchone()[0]
    print(f"backfilling ts in [{lo}, {cut})  "
          f"({datetime.datetime.fromtimestamp(lo)} -> {datetime.datetime.fromtimestamp(cut)})")
    lines, nsec, nmin = [], 0, 0
    for row in con.execute("SELECT * FROM cal_sec WHERE ts<? ORDER BY ts", (cut,)):
        lines += sec_points(row); nsec += 1
        if len(lines) >= 5000:
            wapi.write(bucket=BUCKET, org=ORG, record="\n".join(lines),
                       write_precision=WritePrecision.NS); lines = []
    for row in con.execute("SELECT * FROM cal_min WHERE ts<? ORDER BY ts", (cut,)):
        lines += min_points(row); nmin += 1
        if len(lines) >= 5000:
            wapi.write(bucket=BUCKET, org=ORG, record="\n".join(lines),
                       write_precision=WritePrecision.NS); lines = []
    if lines:
        wapi.write(bucket=BUCKET, org=ORG, record="\n".join(lines),
                   write_precision=WritePrecision.NS)
    print(f"wrote {nsec} sec rows, {nmin} min rows")


if __name__ == "__main__":
    cut = cutoff_ts()
    print(f"cutoff (earliest existing Influx point) = {cut} "
          f"({datetime.datetime.fromtimestamp(cut)})")
    if "--validate" in sys.argv: validate(cut)
    elif "--apply" in sys.argv: apply(cut)
    else: print("pass --validate or --apply")

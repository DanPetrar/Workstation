#!/usr/bin/env python3
"""ZaxModbus MQTT -> InfluxDB parser.
Subscribes to the 10 batch boards' zax_<mac>/sec and /min topics on the local
broker and writes to the dedicated `zaxmodbus` bucket with source=mqtt so the
MQTT path stays separately comparable to the Modbus path (Phase 2 decision #2).
"""
import os
import struct
import time
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

BROKER_HOST = "localhost"          # batch-10 boards publish to the Workstation broker
BROKER_PORT = 1883

INFLUX_URL    = "http://localhost:8086"
# Path is overridable so the decode logic can be exercised off-box (see
# test_zaxmodbus_parser.py). A MISSING token still raises, deliberately: in
# production this must fail loudly at start rather than run and drop writes.
TOKEN_FILE    = os.environ.get("ZAX_TOKEN_FILE", "/opt/zaxmodbus-parser/.token")
INFLUX_TOKEN  = open(TOKEN_FILE).read().strip()
INFLUX_ORG    = "zax"
INFLUX_BUCKET = "zaxmodbus"
SOURCE        = "mqtt"

# zax_<mac tail> -> (unit_name, board_number)
UNITS = {
    "zax_E4A85C": ("ZaxModbus-01", "01"),
    "zax_E4DBCC": ("ZaxModbus-02", "02"),
    "zax_E4AD30": ("ZaxModbus-03", "03"),
    "zax_E44A54": ("ZaxModbus-04", "04"),
    "zax_E48CFC": ("ZaxModbus-05", "05"),
    "zax_E4A7F8": ("ZaxModbus-06", "06"),
    "zax_E4937C": ("ZaxModbus-07", "07"),
    "zax_E49D10": ("ZaxModbus-08", "08"),
    "zax_E539C0": ("ZaxModbus-09", "09"),
    "zax_E54CAC": ("ZaxModbus-10", "10"),
    "zax_E55008": ("ZaxModbus-11", "11"),
    "zax_E44870": ("ZaxModbus-12", "12"),
    "zax_E4A844": ("ZaxModbus-13", "13"),
    "zax_E4E8F8": ("ZaxModbus-14", "14"),
    "zax_E4A898": ("ZaxModbus-15", "15"),
}
PHASES = ["R", "S", "T"]

influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx.write_api(write_options=SYNCHRONOUS)


# ── wire lengths (W2) ────────────────────────────────────────────────────────
# EXACT lengths, never ">=". The 1.2.0 MinRecord puts the import pair first so
# its 28 B prefix is still a valid 1.1.x record (spec B1) — which means a ">= 28"
# test accepts a 52 B record, decodes the import pair correctly, and **silently
# discards the export pair**. Not corruption, but silent loss of half of the
# measurement the 1.2.0 work exists to deliver, with nothing logged. Exact
# dispatch makes an unknown length loud instead.
SEC_LEN    = 76   # ts + v[3] a[3] w[3] hz[3] var[3] pf[3]
MIN_LEN_V1 = 28   # ts + kwh[3] kvarh[3]                        (<= 1.1.x)
MIN_LEN_V2 = 52   # ts + kwh_imp[3] kvarh_imp[3] kwh_exp[3] kvarh_exp[3]  (1.2.0)

# ── timestamp plausibility (W1) ──────────────────────────────────────────────
# A record whose clock was never set carries boot-relative seconds, which become
# 1970 points in InfluxDB — the origin of the pre-2020 rows already in the
# bucket. A corrupt far-future ts is worse still: it breaks `last()` and every
# default dashboard range. Same floor as cal_parser.py and zax_gap_watch.py.
#
# NOTE (philosophy P2): dropping is NOT the intended end state. Data with no
# valid timestamp should be MARKED and kept — stored under its arrival time and
# flagged asynchronous — but the carrier for that mark is still undecided
# (spec B19). Until it exists, refusing loudly beats writing a wrong time
# silently, which is what happened before.
MIN_TS = 1_577_836_800            # 2020-01-01
MAX_SKEW_S = 86_400               # accept at most a day ahead of the receiver


def ts_plausible(ts):
    return MIN_TS <= ts <= (time.time() + MAX_SKEW_S)


_rejects = {}     # (kind, len) -> count, so an unknown shape is reported once


def _reject(kind, payload, unit):
    n = len(payload)
    key = (kind, n)
    _rejects[key] = _rejects.get(key, 0) + 1
    c = _rejects[key]
    if c == 1 or c % 100 == 0:
        print(f"[parser] REJECT {kind} from {unit}: {n} B is not a known length "
              f"(x{c}) — record dropped, not guessed", flush=True)


def decode_sec(payload):
    """-> (ts, fields) or None. Pure: no I/O, so it is testable on its own."""
    if len(payload) != SEC_LEN:
        return None
    f = struct.unpack('<I 3f 3f 3f 3f 3i 3f', payload)
    return (f[0], f) if ts_plausible(f[0]) else None


def decode_min(payload):
    """-> (ts, imp_kwh, imp_kvarh, exp_kwh, exp_kvarh) or None.

    exp_* are None for a 1.1.x record — None, not 0.0: 'this unit does not
    report export' and 'it exported nothing' are different facts, and writing
    a zero would be a derived value the box never sent (philosophy P6).
    """
    n = len(payload)
    if n == MIN_LEN_V1:
        f = struct.unpack('<I 3f 3f', payload)
        return (f[0], f[1:4], f[4:7], None, None) if ts_plausible(f[0]) else None
    if n == MIN_LEN_V2:
        f = struct.unpack('<I 3f 3f 3f 3f', payload)
        return (f[0], f[1:4], f[4:7], f[7:10], f[10:13]) if ts_plausible(f[0]) else None
    return None


def handle_sec(unit, board, payload):
    d = decode_sec(payload)
    if d is None:
        _reject("sec" if len(payload) != SEC_LEN else "sec-ts", payload, unit)
        return
    ts, f = d
    ts_ns = ts * 1_000_000_000
    points = []
    for i, phase in enumerate(PHASES):
        points.append(
            f"power,source={SOURCE},unit={unit},board={board},phase={phase} "
            f"v={f[1+i]},a={f[4+i]},w={f[7+i]},hz={f[10+i]},"
            f"var={f[13+i]}i,pf={f[16+i]} {ts_ns}"
        )
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record="\n".join(points))


def handle_min(unit, board, payload):
    d = decode_min(payload)
    if d is None:
        _reject("min" if len(payload) not in (MIN_LEN_V1, MIN_LEN_V2) else "min-ts",
                payload, unit)
        return
    ts, kwh, kvarh, kwh_exp, kvarh_exp = d
    ts_ns = ts * 1_000_000_000
    points = []
    for i, phase in enumerate(PHASES):
        # Import keeps the existing field names `kwh`/`kvarh`: it is the same
        # physical quantity these series have always carried, so every existing
        # dashboard and query stays valid across the 1.2.0 shift. Export is
        # additive, and simply absent for a 1.1.x record (W3 covers the Grafana
        # side tolerating a missing series).
        fields = f"kwh={kwh[i]},kvarh={kvarh[i]}"
        if kwh_exp is not None:
            fields += f",kwh_exp={kwh_exp[i]},kvarh_exp={kvarh_exp[i]}"
        points.append(
            f"energy,source={SOURCE},unit={unit},board={board},phase={phase} "
            f"{fields} {ts_ns}"
        )
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record="\n".join(points))


def on_message(client, userdata, msg):
    parts = msg.topic.split("/")
    if len(parts) < 2:
        return
    entry = UNITS.get(parts[0])
    if not entry:
        return
    unit, board = entry
    try:
        if parts[1] == "sec":
            handle_sec(unit, board, msg.payload)
        elif parts[1] == "min":
            handle_min(unit, board, msg.payload)
    except Exception as e:
        print(f"[ERROR] {msg.topic}: {e}", flush=True)


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[MQTT] Connected (rc={rc})", flush=True)
    for prefix in UNITS:
        client.subscribe(f"{prefix}/#")
    print(f"[MQTT] Subscribed to {len(UNITS)} board prefixes", flush=True)


# Guarded so the module can be imported for its decode functions without
# connecting to a broker or blocking in loop_forever(). The service runs this
# file as a script, so this path is unchanged in production.
if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="zaxmodbus-parser")
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[PARSER] Connecting to {BROKER_HOST}:{BROKER_PORT} -> bucket {INFLUX_BUCKET} (source={SOURCE})", flush=True)
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.loop_forever()

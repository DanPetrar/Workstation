#!/usr/bin/env python3
import struct
import time
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

BROKER_HOST = "localhost"
BROKER_PORT = 1883

INFLUX_URL    = "http://localhost:8086"
INFLUX_TOKEN  = "REPLACE_WITH_TOKEN_FROM_I-001"
INFLUX_ORG    = "zax"
INFLUX_BUCKET = "zaxenergy"

UNITS = {"zax_E47730": "Unit_A", "zax_E482C0": "Unit_B", "zax_73DA28": "Unit_C", "zax_F07F8C": "Unit_D"}
PHASES = ["R", "S", "T"]

influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx.write_api(write_options=SYNCHRONOUS)


# ── wire lengths (W2) ────────────────────────────────────────────────────────
# EXACT lengths, never ">=" — same reasoning as zaxmodbus_parser.py. The 1.2.0
# MinRecord's import pair comes first so its 28 B prefix is still a valid 1.1.x
# record (spec B1), which means a ">= 28" test accepts a 52 B record, decodes
# import correctly and SILENTLY DROPS the export pair. This parser serves the
# BENCH units (Unit_A..D) — the first machines that will ever run 1.2.0 — so it
# needs the fix at least as urgently as the fleet parser.
SEC_LEN    = 76
MIN_LEN_V1 = 28
MIN_LEN_V2 = 52

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


_rejects = {}


def _reject(kind, payload, unit_name):
    key = (kind, len(payload))
    _rejects[key] = _rejects.get(key, 0) + 1
    c = _rejects[key]
    if c == 1 or c % 100 == 0:
        print(f"[parser] REJECT {kind} from {unit_name}: {len(payload)} B is not a "
              f"known length (x{c}) — record dropped, not guessed", flush=True)


def decode_min(payload):
    """-> (ts, kwh, kvarh, kwh_exp, kvarh_exp) or None; exp are None for 1.1.x.

    None rather than 0.0 on purpose: "does not report export" and "exported
    nothing" are different facts, and a zero would invent a value the box never
    sent.
    """
    n = len(payload)
    if n == MIN_LEN_V1:
        f = struct.unpack('<I 3f 3f', payload)
        return (f[0], f[1:4], f[4:7], None, None) if ts_plausible(f[0]) else None
    if n == MIN_LEN_V2:
        f = struct.unpack('<I 3f 3f 3f 3f', payload)
        return (f[0], f[1:4], f[4:7], f[7:10], f[10:13]) if ts_plausible(f[0]) else None
    return None


def handle_sec(unit_name, payload):
    if len(payload) != SEC_LEN:
        _reject("sec", payload, unit_name)
        return
    f = struct.unpack('<I 3f 3f 3f 3f 3i 3f', payload)
    if not ts_plausible(f[0]):
        _reject("sec-ts", payload, unit_name)
        return
    ts_ns = f[0] * 1_000_000_000
    points = []
    for i, phase in enumerate(PHASES):
        points.append(
            f"power,unit={unit_name},phase={phase} "
            f"v={f[1+i]},a={f[4+i]},w={f[7+i]},hz={f[10+i]},"
            f"var={f[13+i]}i,pf={f[16+i]} {ts_ns}"
        )
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record="\n".join(points))


def handle_min(unit_name, payload):
    d = decode_min(payload)
    if d is None:
        _reject("min" if len(payload) not in (MIN_LEN_V1, MIN_LEN_V2) else "min-ts",
                payload, unit_name)
        return
    ts, kwh, kvarh, kwh_exp, kvarh_exp = d
    ts_ns = ts * 1_000_000_000
    points = []
    for i, phase in enumerate(PHASES):
        # Import keeps the existing field names so current dashboards and
        # queries stay valid; export is additive and simply absent for 1.1.x.
        fields = f"kwh={kwh[i]},kvarh={kvarh[i]}"
        if kwh_exp is not None:
            fields += f",kwh_exp={kwh_exp[i]},kvarh_exp={kvarh_exp[i]}"
        points.append(
            f"energy,unit={unit_name},phase={phase} {fields} {ts_ns}"
        )
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record="\n".join(points))


def on_message(client, userdata, msg):
    topic_parts = msg.topic.split("/")
    if len(topic_parts) < 2:
        return
    prefix = topic_parts[0]
    mtype  = topic_parts[1]
    unit_name = UNITS.get(prefix)
    if not unit_name:
        return
    try:
        if mtype == "sec":
            handle_sec(unit_name, msg.payload)
        elif mtype == "min":
            handle_min(unit_name, msg.payload)
    except Exception as e:
        print(f"[ERROR] {msg.topic}: {e}")


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[MQTT] Connected (rc={rc})")
    for prefix in UNITS:
        client.subscribe(f"{prefix}/#")
        print(f"[MQTT] Subscribed to {prefix}/#")


# Guarded so the module can be imported for its decode functions without
# constructing a client, connecting, or blocking in loop_forever(). The service
# runs this file as a script, so production is unchanged.
if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="zax-parser")
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[PARSER] Connecting to {BROKER_HOST}:{BROKER_PORT} ...")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_forever()

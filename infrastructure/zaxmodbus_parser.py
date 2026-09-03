#!/usr/bin/env python3
"""ZaxModbus MQTT -> InfluxDB parser.
Subscribes to the 10 batch boards' zax_<mac>/sec and /min topics on the local
broker and writes to the dedicated `zaxmodbus` bucket with source=mqtt so the
MQTT path stays separately comparable to the Modbus path (Phase 2 decision #2).
"""
import struct
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

BROKER_HOST = "localhost"          # batch-10 boards publish to the Workstation broker
BROKER_PORT = 1883

INFLUX_URL    = "http://localhost:8086"
INFLUX_TOKEN  = open("/opt/zaxmodbus-parser/.token").read().strip()
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


def handle_sec(unit, board, payload):
    if len(payload) < 76:
        return
    f = struct.unpack('<I 3f 3f 3f 3f 3i 3f', payload[:76])
    ts = f[0]
    if ts == 0:               # clock not set yet -> skip (no valid wall-clock)
        return
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
    if len(payload) < 28:     # 28 B on the wire (struct _pad stripped by firmware)
        return
    f = struct.unpack('<I 3f 3f', payload[:28])
    ts = f[0]
    if ts == 0:
        return
    ts_ns = ts * 1_000_000_000
    points = []
    for i, phase in enumerate(PHASES):
        points.append(
            f"energy,source={SOURCE},unit={unit},board={board},phase={phase} "
            f"kwh={f[1+i]},kvarh={f[4+i]} {ts_ns}"
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


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="zaxmodbus-parser")
client.on_connect = on_connect
client.on_message = on_message

print(f"[PARSER] Connecting to {BROKER_HOST}:{BROKER_PORT} -> bucket {INFLUX_BUCKET} (source={SOURCE})", flush=True)
client.connect(BROKER_HOST, BROKER_PORT, 60)
client.loop_forever()

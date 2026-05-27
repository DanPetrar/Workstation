#!/usr/bin/env python3
import struct
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

BROKER_HOST = "192.168.110.225"
BROKER_PORT = 1883

INFLUX_URL    = "http://localhost:8086"
INFLUX_TOKEN  = "REPLACE_WITH_TOKEN_FROM_I-001"
INFLUX_ORG    = "zax"
INFLUX_BUCKET = "zaxenergy"

UNITS = {"zax_E47730": "Unit_A", "zax_73DA28": "Unit_C"}
PHASES = ["R", "S", "T"]

influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx.write_api(write_options=SYNCHRONOUS)


def handle_sec(unit_name, payload):
    if len(payload) < 76:
        return
    f = struct.unpack('<I 3f 3f 3f 3f 3i 3f', payload[:76])
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
    if len(payload) < 28:
        return
    f = struct.unpack('<I 3f 3f', payload[:28])
    ts_ns = f[0] * 1_000_000_000
    points = []
    for i, phase in enumerate(PHASES):
        points.append(
            f"energy,unit={unit_name},phase={phase} "
            f"kwh={f[1+i]},kvarh={f[4+i]} {ts_ns}"
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


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="zax-parser")
client.on_connect = on_connect
client.on_message = on_message

print(f"[PARSER] Connecting to {BROKER_HOST}:{BROKER_PORT} ...")
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
client.loop_forever()

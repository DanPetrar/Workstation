# TASK I-003 — Python MQTT→InfluxDB parser + systemd service

**Assigned by:** Pi Claude  
**Direction:** Infrastructure stack  
**Depends on:** I-001 ✅ (need token, org, bucket)  
**Status:** Ready

---

## Goal

Write a Python service that subscribes to the Pi's MQTT broker, decodes ZaxEnergy binary payloads, and writes structured data to InfluxDB. Run it as a systemd service so it starts on boot and restarts on failure.

---

## Context

**Pi MQTT broker:** `192.168.110.225:1883` (anonymous access, no credentials)  
**Topics to subscribe:** `zax_E47730/#` and `zax_73DA28/#` (Unit A and Unit C)  
**InfluxDB:** `http://localhost:8086`, org `zax`, bucket `zaxenergy`  
**Token:** from `setup/I-001-influxdb.md`

### Binary payload formats

`<prefix>/sec` — 76 bytes, little-endian:
```
uint32  ts      Unix timestamp (seconds)
float×3 v       Voltage V      — R, S, T  (index 1,2,3)
float×3 a       Current A      — R, S, T  (index 4,5,6)
float×3 w       Active power W — R, S, T  (index 7,8,9)
float×3 hz      Frequency Hz   — R, S, T  (index 10,11,12)
int32×3 var     Reactive VAr   — R, S, T  (index 13,14,15)
float×3 pf      Power factor   — R, S, T  (index 16,17,18)
```
Python: `struct.unpack('<I 3f 3f 3f 3f 3i 3f', payload)` → 19 values

`<prefix>/min` — 28 bytes, little-endian:
```
uint32  ts      Unix timestamp (seconds)
float×3 kwh     Active energy kWh   — R, S, T
float×3 kvarh   Reactive energy kVArh — R, S, T
```
Python: `struct.unpack('<I 3f 3f', payload[:28])` → 7 values

### Unit map (prefix → name)
```python
UNITS = {
    "zax_E47730": "Unit_A",
    "zax_73DA28": "Unit_C",
}
```

---

## InfluxDB data model

Write two measurements:

**`power`** — from `/sec` topic, one point per second per phase:
- Tags: `unit` (e.g. `Unit_A`), `phase` (`R`, `S`, or `T`)
- Fields: `v` (float), `a` (float), `w` (float), `hz` (float), `var` (int), `pf` (float)
- Timestamp: `ts` field from payload (nanoseconds for InfluxDB line protocol: `ts * 1_000_000_000`)

**`energy`** — from `/min` topic, one point per minute per phase:
- Tags: `unit`, `phase`
- Fields: `kwh` (float), `kvarh` (float)
- Timestamp: `ts` field from payload (nanoseconds)

---

## Implementation

### Install dependencies

```bash
pip3 install paho-mqtt influxdb-client
```

### Script location

`/opt/zax-parser/zax_parser.py`

```python
#!/usr/bin/env python3
"""
zax_parser.py — ZaxEnergy MQTT→InfluxDB bridge.
Subscribes to Pi broker, decodes binary payloads, writes to InfluxDB.
"""

import struct
import time
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS

BROKER_HOST = "192.168.110.225"
BROKER_PORT = 1883

INFLUX_URL    = "http://localhost:8086"
INFLUX_TOKEN  = "REPLACE_WITH_TOKEN_FROM_I-001"
INFLUX_ORG    = "zax"
INFLUX_BUCKET = "zaxenergy"

UNITS = {
    "zax_E47730": "Unit_A",
    "zax_73DA28": "Unit_C",
}

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
```

### Systemd service

`/etc/systemd/system/zax-parser.service`:

```ini
[Unit]
Description=ZaxEnergy MQTT→InfluxDB Parser
After=network.target influxdb.service
Wants=network.target

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/python3 /opt/zax-parser/zax_parser.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Install and start

```bash
sudo mkdir -p /opt/zax-parser
sudo cp zax_parser.py /opt/zax-parser/zax_parser.py

# Insert real token into the script
sudo sed -i 's/REPLACE_WITH_TOKEN_FROM_I-001/<ACTUAL_TOKEN>/' /opt/zax-parser/zax_parser.py

sudo cp zax-parser.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable zax-parser
sudo systemctl start zax-parser

# Verify
sudo systemctl status zax-parser
sudo journalctl -u zax-parser -f
```

---

## Verification

After the service starts, wait 90 seconds (at least one `/sec` and one possible `/min`), then query InfluxDB:

```bash
TOKEN=$(grep token setup/I-001-influxdb.md | awk '{print $2}')

influx query --org zax --token $TOKEN \
  'from(bucket:"zaxenergy")
   |> range(start: -5m)
   |> filter(fn: (r) => r._measurement == "power")
   |> limit(n: 5)'
```

Expected: rows with `unit=Unit_A` or `unit=Unit_C`, fields v/a/w/hz/var/pf.

---

## Deliverables

1. **Commit `/opt/zax-parser/zax_parser.py`** to this repo at `infrastructure/zax_parser.py` (without the real token — replace it back with `REPLACE_WITH_TOKEN_FROM_I-001` before committing)
2. **Commit `infrastructure/zax-parser.service`** systemd unit
3. **Create `setup/I-003-parser.md`** — confirm service running, sample query output
4. **Update `inventory.md`** — add `zax-parser` service row
5. **Update `tasks/INDEX.md`** — mark I-003 Done
6. **Commit and push** — message: `I-003: MQTT→InfluxDB parser installed and running`

---

## Acceptance criteria

- `systemctl status zax-parser` shows active (running)
- InfluxDB `power` measurement has data from Unit_A and/or Unit_C
- No errors in `journalctl -u zax-parser` after 2 minutes of runtime
- Token not committed to git (placeholder only in repo copy)

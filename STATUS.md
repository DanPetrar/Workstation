# Current Status — ZaxEnergy Infrastructure

_Updated: 2026-06-22 by Pi Claude_

## Active tasks

_None — fleet expansion (Board_11+12) complete. Awaiting next direction from Pi._

## Completed directions

### Fleet expansion — Board_11 + Board_12 ✅ (2026-06-22)
Two new S3-Zero boards added to the ZaxModbus fleet:
- **Board_11:** MAC 3c:0f:02:e5:50:08, topic `zax_E55008`, slave 11, IP .131 — commission PASS (100% Modbus/MQTT)
- **Board_12:** MAC 3c:0f:02:e4:48:70, topic `zax_E44870`, slave 12, IP .121 — commission PASS (100% Modbus/94% MQTT)
- Parser `zaxmodbus-parser.service` updated (12 boards) + redeployed ✅
- Grafana dashboards pushed: fleet/board/dq now show boards 01–12, threshold=12 ✅
- Pi poller updated to `SLAVES=range(1,13)` ✅

### ZaxModbus fleet (12 boards) ✅
All 12 Waveshare S3-Zero boards on **v1.0.2**:
- MQTT path: boards → Workstation broker → `zaxmodbus-parser` → InfluxDB `zaxmodbus` bucket
- Modbus path: Pi RS-485 (`/dev/ttyUSB0`) → `zaxmodbus-poller` → InfluxDB `zaxmodbus` bucket
- Both pipelines verified; Grafana dashboards live

### Pi→Workstation migration ✅ (2026-06-03)
All services on Workstation:
- InfluxDB v2.7.11 — org `zax`, buckets `zaxenergy` + `zaxmodbus`
- Grafana 13.0.1 — http://192.168.110.11:3000 (admin: `zaxenergy2026`)
- EnergyCalibrator bench pipeline (collector → SQLite → reports/PDFs at :8080)

### Infrastructure stack ✅
All services running on Workstation (192.168.110.11):
- `zaxmodbus-parser.service` — 12 ZaxModbus boards, MQTT → InfluxDB
- `zax-parser.service` — Unit_A + Unit_C ZaxEnergySurvey data → InfluxDB
- `cal_collector.service` — EnergyCalibrator bench data → SQLite
- `cal_reports.service` — session UI + PDFs at http://192.168.110.11:8080
- `cal-parser.service` — EnergyCalibrator → InfluxDB
- `grafana-server.service` — http://192.168.110.11:3000
- `mosquitto.service` — :1883 (ZaxModbus boards + EnergyCalibrator bench)

## Quick reference

| Item | Value |
|------|-------|
| SSH | `ssh ws` (dan-linux, key-based, passwordless sudo) |
| Grafana | http://192.168.110.11:3000 — admin `zaxenergy2026` |
| InfluxDB | http://192.168.110.11:8086 — org `zax`, buckets: `zaxenergy`, `zaxmodbus` |
| MQTT broker | `192.168.110.11:1883` (anonymous) |
| Session UI | http://192.168.110.11:8080 |
| ZaxModbus parser | `/opt/zaxmodbus-parser/zaxmodbus_parser.py` |
| ZaxModbus token | `/opt/zaxmodbus-parser/.token` |
| Grafana password reset | Stop service first: `sudo systemctl stop grafana-server` then `sudo grafana cli --homepath /usr/share/grafana admin reset-admin-password zaxenergy2026` then `sudo systemctl start grafana-server` |
| Grafana dashboards update | From Pi: `GRAFANA_PW=zaxenergy2026 python3 ZaxModbus/tools/phase2/grafana_dashboards.py` (pipe via `ssh ws`) |
| Flutter | `/opt/flutter/bin/flutter` |
| InfluxDB CLI org | always `--org zax` |

---

## Convention

- **Start of session:** read this file first — all service URLs and credentials here
- **Pi session:** Pi has direct SSH (`ssh ws`) + passwordless sudo — no Workstation Claude needed for infra tasks
- **Task done:** update this file; keep Quick reference table current

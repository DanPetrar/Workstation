# Workstation — Task Index

_Maintained by Pi Claude. Updated after every task completion._

---

## Workstation setup (W-)

| ID | Title | Status | Result |
|----|-------|--------|--------|
| W-001 | Inventory current tools and environment | **Done** | Flutter/Java/adb not installed; data stack (Influx, Grafana, Mosquitto) already running; Pi reachable |

## Infrastructure stack (I-)

| ID | Title | Status | Result |
|----|-------|--------|--------|
| I-001 | Install and verify InfluxDB 2.x | Waiting on W-001 | — |
| I-002 | Install and verify Grafana | Waiting on W-001 | — |
| I-003 | Write MQTT→InfluxDB parser for ZaxEnergy payloads | Waiting on I-001 | — |
| I-004 | Connect parser to live units, verify data in InfluxDB | Waiting on I-003 | — |
| I-005 | Build Grafana dashboards (power + energy) | Waiting on I-004 | — |

## Android app — see ZaxEnergySurvey/android/tasks/

| ID | Title | Status |
|----|-------|--------|
| ANDROID-001 | Setup Flutter environment and verify | Waiting on W-001 |

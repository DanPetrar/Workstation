# Workstation — Task Index

_Maintained by Pi Claude. Updated after every task completion._

---

## Workstation setup (W-)

| ID | Title | Status | Result |
|----|-------|--------|--------|
| W-001 | Inventory current tools and environment | ✅ Done | Flutter/Java/adb not installed; InfluxDB+Grafana+Mosquitto already running; Pi reachable at 0.285ms |

## Infrastructure stack (I-)

| ID | Title | Status | Result |
|----|-------|--------|--------|
| I-001 | Verify and configure InfluxDB for ZaxEnergy | ✅ Done | v2.7.11, org `zax`, bucket `zaxenergy`, scoped token created, write/read verified |
| I-002 | Verify and configure Grafana → InfluxDB connection | **Ready** | — |
| I-003 | Python MQTT→InfluxDB parser + systemd service | **Ready** | — |
| I-004 | Build Grafana dashboards (power + energy) | Waiting on I-002 + I-003 | — |

## Android app — see ZaxEnergySurvey/android/tasks/

| ID | Title | Status |
|----|-------|--------|
| ANDROID-001 | Setup Flutter + Java environment | Not started |

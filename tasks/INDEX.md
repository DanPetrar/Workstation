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
| I-002 | Verify and configure Grafana → InfluxDB connection | ✅ Done | Grafana 13.0.1, data source `ZaxEnergy-InfluxDB` (UID `ffnbf64waxe68a`) added; health check OK — 1 bucket found |
| I-003 | Python MQTT→InfluxDB parser + systemd service | ✅ Done | zax-parser.service active; Unit_A + Unit_C data flowing into InfluxDB `power` + `energy` measurements |
| I-004 | Build Grafana dashboards (power + energy) | ✅ Done | Power (6 panels, unit dropdown) + Energy (2 panels) dashboards live; admin password changed |

## Android app — see ZaxEnergySurvey/android/tasks/

| ID | Title | Status | Result |
|----|-------|--------|--------|
| ANDROID-001 | Setup Flutter + Java environment | ✅ Done | Flutter 3.44.0 + Java 17 + Android SDK 36; debug APK build verified |
| ANDROID-002 | Flutter app scaffold — unit list + nav skeleton | ✅ Done | Unit list screen with online/offline check; Live + Config nav skeletons; APK built, analyze clean |
| ANDROID-003 | Live dashboard screen — /api/data polling | ✅ Done | Polls /api/data every 2 s; actual API shape differs from spec — implemented against real response |
| ANDROID-004 | Config screen — read/write /api/config | ✅ Done | Loads /api/config, edits Device + MQTT fields, POSTs on save; analyze clean, APK built |
| ANDROID-005 | Headless Android emulator | ✅ Done | KVM ok; AVD `zax_test` (Nexus 4, API 36); clean screenshot, no ANR after profile fix |
| ANDROID-006 | Live dashboard screenshot + subtitle fix | ✅ Done | Subtitle fix (mqtt_topic removed); live dashboard screenshot: Unit C, 240.40 V, 50.01 Hz |
| ANDROID-007 | Config screen screenshot for demo doc | **Ready** | — |

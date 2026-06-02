# Current Status — ZaxEnergy Infrastructure

_Updated: 2026-06-02 by Pi Claude_

## Active tasks

**Pi→Workstation migration in progress** (runbook: `MIGRATION-pi-to-workstation.md`).
- **Phase A — direct SSH control: ✅ COMPLETE.** Pi session reaches this machine via
  `ssh ws` (key-based, passwordless sudo). GitHub hand-off is now the fallback.
- **Phase B — provision (no cutover): ✅ COMPLETE.**
  - EnergyCalibrator cloned → `/workspace/projects/EnergyCalibrator` (HEAD `d574f98`).
  - venv `.venv` with `paho-mqtt 2.1`, `reportlab 4.5`, `influxdb-client 1.50` (Python 3.14).
  - DB dir `/workspace/cal-data/` created (empty).
  - Broker: anonymous `:1883` — matches Unit D; no credential change needed.
  - Bench parser planned (sec = 76-byte `<I 3f 3f 3f 3f 3i 3f`; min = JSON) — wiring deferred to Phase C6.
- **Phase C — cutover IN PROGRESS (paused before C4):**
  - **C1 ✅** Parallel-run collector live on Workstation (pid in `/workspace/cal-data/collector.pid`), subscribed to **Pi broker .225**, writing `/workspace/cal-data/cal_data.db`. **Must keep running until C4.** Pi collector still primary.
  - **C2 ✅** Shared-window cross-check: Pi vs WS identical (259 sec rows, ΣW 345516.0, 4 min rows, Σdkwh 0.03/0.03/0.03).
  - **C3 ✅** Full Pi history merged into WS DB (idempotent, PK ts+unit); reconciled — both have cal_sec 178649 / cal_min 3029 up to snapshot boundary.
  - **C4 ✅ CUTOVER DONE (no data loss).** Unit D `mqtt_host` now `.11`; WS collector reads **local broker** (~1s lag); Pi `cal_collector` **inactive+disabled**. Final reconciliation: both DBs identical to Pi freeze (sec 178986 / min 3035); WS now live-ahead.
  - **C5 ✅ services + crons moved.** WS systemd: `cal_collector.service` (active+enabled, local broker) and `cal_reports.service` (active+enabled, http://192.168.110.11:8080/). Crons in `dan-linux` crontab: daily report 00:05 (`/workspace/cal-data/ws_daily_report.sh`, passes `--db`), prune 00:30 Mon–Sat, prune+vacuum Sun. Pi bench crons removed. Report gen smoke-tested (2026-06-01 PDF: 1416 min / 83348 sec rows).
  - **Next: C6** InfluxDB cal feed + Grafana bench panel; **C7** e2e verify; **C8** decommission Pi bench (disable Pi `cal_reports.service`; archive Pi `cal_data.db`; **leave Pi broker — ZAX still uses it**).

## Completed directions

### Infrastructure stack ✅
All services running on Workstation (192.168.110.11):
- InfluxDB v2.7.11 — org `zax`, bucket `zaxenergy`
- Grafana 13.0.1 — http://192.168.110.11:3000 (admin: `zaxenergy2026`)
- zax-parser.service — Unit_A + Unit_C live data flowing

### Android demo app ✅ — verified + documented
Flutter app at `ZaxEnergySurvey/android/zax_monitor/`:
- Unit list, live dashboard, config screen — all working against live hardware
- Emulator: AVD `zax_test` (Nexus 4, API 36, KVM), `~/start-zax-emulator.sh`
- Presentation: `ZaxEnergySurvey/android/ZaxMonitor_Demo.md` (all 3 screenshots)

## Quick reference

| Item | Value |
|------|-------|
| InfluxDB | http://localhost:8086, org `zax`, bucket `zaxenergy` |
| Grafana | http://192.168.110.11:3000, admin `zaxenergy2026` |
| Parser service | `systemctl status zax-parser` |
| Flutter | `/opt/flutter/bin/flutter` |
| Emulator | `~/start-zax-emulator.sh` |
| App repo | `git@github.com:DanPetrar/ZaxEnergySurvey.git`, `android/zax_monitor/` |
| Demo doc | `ZaxEnergySurvey/android/ZaxMonitor_Demo.md` |
| Tap coords (Nexus 4) | Unit C dashboard: x=575, y=375 — Config: x=669, y=375 |

---

## Convention

- **Start of session:** read this file first — no need to load full task specs
- **Task done:** update this file + `tasks/INDEX.md` + write `setup/XXX.md` in one commit; set status to `Done — awaiting Pi review`
- **Pi review:** reads `setup/XXX.md`, fixes issues, updates status to `Ready` for next task
- **User handoff:** short message only — "ANDROID-008 ready", etc.

# Current Status — ZaxEnergy Infrastructure

_Updated: 2026-05-27 by Pi Claude_

## Active tasks

_None — Android demo verified end-to-end. Awaiting next direction from Pi._

## Completed directions

### Infrastructure stack ✅
All services running on Workstation (192.168.110.11):
- InfluxDB v2.7.11 — org `zax`, bucket `zaxenergy`
- Grafana 13.0.1 — http://192.168.110.11:3000 (admin: `zaxenergy2026`)
- zax-parser.service — Unit_A + Unit_C live data flowing

### Android demo app ✅ — verified on emulator
Flutter app at `ZaxEnergySurvey/android/zax_monitor/`:
- Unit list — both units online, clean subtitles, Live + Config navigation
- Live dashboard — real data from Unit C: 240.40 V, 50.01 Hz, timestamps correct
- Config screen — Device + MQTT fields, GET load + POST save
- Emulator: AVD `zax_test` (Nexus 4, API 36, KVM), `~/start-zax-emulator.sh`

## Quick reference

| Item | Value |
|------|-------|
| InfluxDB | http://localhost:8086, org `zax`, bucket `zaxenergy` |
| Grafana | http://192.168.110.11:3000, admin `zaxenergy2026` |
| Parser service | `systemctl status zax-parser` |
| Flutter | `/opt/flutter/bin/flutter` |
| Emulator | `~/start-zax-emulator.sh` |
| App repo | `git@github.com:DanPetrar/ZaxEnergySurvey.git`, `android/zax_monitor/` |
| Tap coords (Nexus 4) | Unit C dashboard icon: x=575, y=375 |

---

## Convention

- **Start of session:** read this file first — no need to load full task specs
- **Task done:** update this file + `tasks/INDEX.md` + write `setup/XXX.md` in one commit; set status to `Done — awaiting Pi review`
- **Pi review:** reads `setup/XXX.md`, fixes issues, updates status to `Ready` for next task
- **User handoff:** short message only — "ANDROID-007 ready", etc.

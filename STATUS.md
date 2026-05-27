# Current Status — ZaxEnergy Infrastructure

_Updated: 2026-05-27 by Pi Claude_

## Active tasks

_None — both directions complete. Awaiting next direction from Pi._

## Completed directions

### Infrastructure stack ✅
All services running on Workstation (192.168.110.11):
- InfluxDB v2.7.11 — org `zax`, bucket `zaxenergy`
- Grafana 13.0.1 — dashboards at http://192.168.110.11:3000/d/zax-power and /d/zax-energy
- zax-parser.service — Unit_A + Unit_C data flowing live

### Android demo app ✅
Flutter app at `ZaxEnergySurvey/android/zax_monitor/`:
- Unit list with online/offline status (Unit_A .152, Unit_C .125)
- Live dashboard — per-phase V/A/W/Hz/PF/VAr + totals, polls /api/data every 2s
- Config screen — Device + MQTT fields, GET load + POST save

## Quick reference

| Item | Value |
|------|-------|
| InfluxDB | http://localhost:8086, org `zax`, bucket `zaxenergy` |
| Grafana | http://192.168.110.11:3000, admin `zaxenergy2026` |
| Parser service | `systemctl status zax-parser` |
| Flutter | `/opt/flutter/bin/flutter` |
| App repo | `git@github.com:DanPetrar/ZaxEnergySurvey.git`, `android/zax_monitor/` |

---

## Convention

- **Start of session:** read this file first — no need to load full task specs
- **Task done:** update this file + `tasks/INDEX.md` + write `setup/XXX.md` in one commit; set status to `Done — awaiting Pi review`
- **Pi review:** reads `setup/XXX.md`, fixes issues, updates status to `Ready` for next task
- **User handoff:** short message only — "ANDROID-005 ready", etc.

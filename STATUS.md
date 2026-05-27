# Current Status — ZaxEnergy Infrastructure

_Updated: 2026-05-27 by Pi Claude_

## Active tasks

| Task | Status | Assigned to |
|------|--------|-------------|
| — | — | Done — awaiting Pi review |

## Blocking / notes

- Infrastructure stack complete (I-001 through I-004 all ✅)
- Flutter 3.44.0 stable at `/opt/flutter`; ANDROID_HOME at `/home/dan-linux/Android/Sdk`
- ZaxEnergySurvey repo: `git@github.com:DanPetrar/ZaxEnergySurvey.git`
- App lives in `ZaxEnergySurvey/android/zax_monitor/` (to be created in ANDROID-002)
- Unit_A: 192.168.110.152 — Unit_C: 192.168.110.125

## Done (last 5)

| Task | Result |
|------|--------|
| ANDROID-002 | Unit list + nav skeleton; APK built, flutter analyze clean |
| ANDROID-001 | Flutter 3.44.0 + Java 17.0.18 + Android SDK API 36; debug APK ✅ |
| I-004 | Power (6 panels) + Energy (2 panels) dashboards live at http://192.168.110.11:3000 |
| I-003 | zax-parser.service active; Unit_A + Unit_C flowing into InfluxDB |
| I-002 | Grafana datasource `ZaxEnergy-InfluxDB` (UID `ffnbf64waxe68a`) connected |
| I-001 | InfluxDB v2.7.11, org `zax`, bucket `zaxenergy` |

## Next unlock

| Condition | Unlocks |
|-----------|---------|
| ANDROID-002 ✅ | ANDROID-003 (live data screen) |

---

## Convention

- **Start of session:** read this file first — no need to load full task specs
- **Task done:** update this file + `tasks/INDEX.md` + write `setup/ANDROID-XXX.md` in one commit; set status to `Done — awaiting Pi review`
- **Pi review:** reads `setup/ANDROID-XXX.md`, fixes issues, updates status to `Ready` for next task
- **User handoff:** short message only — "ANDROID-002 ready", etc.

# Current Status — ZaxEnergy Infrastructure

_Updated: 2026-05-27 by Pi Claude_

## Active tasks

| Task | Status | Assigned to |
|------|--------|-------------|
| ANDROID-003 | Ready | Workstation |

## Blocking / notes

- Infrastructure stack complete (I-001 through I-004 all ✅)
- App scaffold at `ZaxEnergySurvey/android/zax_monitor/`
- `/api/data` response shape documented in ANDROID-003 spec — verify actual fields match when implementing
- Unit_A: 192.168.110.152 — Unit_C: 192.168.110.125

## Done (last 5)

| Task | Result |
|------|--------|
| ANDROID-002 | Unit list + nav skeleton; APK ✅, analyze clean; committed to ZaxEnergySurvey |
| ANDROID-001 | Flutter 3.44.0 + Java 17.0.18 + Android SDK API 36; debug APK ✅ |
| I-004 | Power (6 panels) + Energy (2 panels) dashboards live at http://192.168.110.11:3000 |
| I-003 | zax-parser.service active; Unit_A + Unit_C flowing into InfluxDB |
| I-002 | Grafana datasource `ZaxEnergy-InfluxDB` (UID `ffnbf64waxe68a`) connected |

## Next unlock

| Condition | Unlocks |
|-----------|---------|
| ANDROID-003 ✅ | ANDROID-004 (config screen) |

---

## Convention

- **Start of session:** read this file first — no need to load full task specs
- **Task done:** update this file + `tasks/INDEX.md` + write `setup/ANDROID-XXX.md` in one commit; set status to `Done — awaiting Pi review`
- **Pi review:** reads `setup/ANDROID-XXX.md`, fixes issues, updates status to `Ready` for next task
- **User handoff:** short message only — "ANDROID-003 ready", etc.

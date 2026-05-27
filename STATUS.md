# Current Status — ZaxEnergy Infrastructure

_Updated: 2026-05-27 by Pi Claude_

## Active tasks

| Task | Status | Assigned to |
|------|--------|-------------|
| ANDROID-004 | Ready | Workstation |

## Blocking / notes

- Infrastructure stack complete (I-001 through I-004 all ✅)
- **Real `/api/data` shape** (see setup/ANDROID-003-live.md): nested under `sec.R/S/T` and `min.R/S/T`, not flat arrays
- **Real `/api/config` shape** verified from Pi: memo, ntp_srv, tz_offset, mqtt_en, mqtt_host, mqtt_port, mqtt_topic (editable); dev_name, ssid read-only
- Unit_A: 192.168.110.152 — Unit_C: 192.168.110.125

## Done (last 5)

| Task | Result |
|------|--------|
| ANDROID-003 | Live dashboard polling /api/data every 2s; per-phase V/A/W/Hz/PF/VAr + totals |
| ANDROID-002 | Unit list + nav skeleton; APK ✅, analyze clean |
| ANDROID-001 | Flutter 3.44.0 + Java 17.0.18 + Android SDK API 36 |
| I-004 | Power + Energy dashboards live at http://192.168.110.11:3000 |
| I-003 | zax-parser.service active; Unit_A + Unit_C flowing into InfluxDB |

## Next unlock

| Condition | Unlocks |
|-----------|---------|
| ANDROID-004 ✅ | Demo app complete — Pi review + planning next direction |

---

## Convention

- **Start of session:** read this file first — no need to load full task specs
- **Task done:** update this file + `tasks/INDEX.md` + write `setup/ANDROID-XXX.md` in one commit; set status to `Done — awaiting Pi review`
- **Pi review:** reads `setup/ANDROID-XXX.md`, fixes issues, updates status to `Ready` for next task
- **User handoff:** short message only — "ANDROID-004 ready", etc.

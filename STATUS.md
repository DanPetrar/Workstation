# Current Status — ZaxEnergy Infrastructure

_Updated: 2026-05-27 by Pi Claude_

## Active tasks

| Task | Status | Assigned to |
|------|--------|-------------|
| ANDROID-007 | Ready | Workstation |

## Blocking / notes

- Infrastructure stack complete (I-001 through I-004 all ✅)
- Emulator: `~/start-zax-emulator.sh`, AVD `zax_test` (Nexus 4, API 36)
- Config gear icon coords (Nexus 4): x=669, y=375

## Done (last 5)

| Task | Result |
|------|--------|
| ANDROID-006 | Subtitle fix; live dashboard screenshot: Unit C 240.40 V, 50.01 Hz |
| ANDROID-005 | KVM ok; AVD `zax_test` (Nexus 4, API 36); clean screenshot, no ANR |
| ANDROID-004 | Config screen: Device + MQTT fields, GET load + POST save; APK ✅ |
| ANDROID-003 | Live dashboard polling /api/data every 2s; per-phase V/A/W/Hz/PF/VAr + totals |
| ANDROID-002 | Unit list + nav skeleton; APK ✅, analyze clean |

## Next unlock

| Condition | Unlocks |
|-----------|---------|
| ANDROID-007 ✅ | Pi completes demo presentation doc (`ZaxMonitor_Demo.md`) |

---

## Convention

- **Start of session:** read this file first — no need to load full task specs
- **Task done:** update this file + `tasks/INDEX.md` + write `setup/XXX.md` in one commit; set status to `Done — awaiting Pi review`
- **Pi review:** reads `setup/XXX.md`, fixes issues, updates status to `Ready` for next task
- **User handoff:** short message only — "ANDROID-007 ready", etc.

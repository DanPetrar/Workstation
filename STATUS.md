# Current Status — ZaxEnergy Infrastructure

_Updated: 2026-05-27 by Pi Claude_

## Active tasks

| Task | Status | Assigned to |
|------|--------|-------------|
| ANDROID-006 | Ready | Workstation |

## Blocking / notes

- Infrastructure stack complete (I-001 through I-004 all ✅)
- Emulator: AVD `zax_test` (Nexus 4, API 36), KVM, no ANR ✅
- Unit C (192.168.110.125) reachable from emulator via host routing ✅
- Unit A (192.168.110.152) not reachable from emulator — expected

## Done (last 5)

| Task | Result |
|------|--------|
| ANDROID-005 | KVM ok; AVD `zax_test` (Nexus 4, API 36); clean screenshot, no ANR |
| ANDROID-004 | Config screen: Device + MQTT fields, GET load + POST save; APK ✅ |
| ANDROID-003 | Live dashboard polling /api/data every 2s; per-phase V/A/W/Hz/PF/VAr + totals |
| ANDROID-002 | Unit list + nav skeleton; APK ✅, analyze clean |
| ANDROID-001 | Flutter 3.44.0 + Java 17.0.18 + Android SDK API 36 |

## Next unlock

| Condition | Unlocks |
|-----------|---------|
| ANDROID-006 ✅ | Demo app verified end-to-end on emulator — Pi reviews, plans next direction |

---

## Convention

- **Start of session:** read this file first — no need to load full task specs
- **Task done:** update this file + `tasks/INDEX.md` + write `setup/XXX.md` in one commit; set status to `Done — awaiting Pi review`
- **Pi review:** reads `setup/XXX.md`, fixes issues, updates status to `Ready` for next task
- **User handoff:** short message only — "ANDROID-006 ready", etc.

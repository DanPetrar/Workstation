# Current Status — ZaxEnergy Infrastructure

_Updated: 2026-05-27 by Pi Claude_

## Active tasks

| Task | Status | Assigned to |
|------|--------|-------------|
| ANDROID-005 | Ready | Workstation |

## Blocking / notes

- ANDROID-005 requires KVM — check `kvm-ok` first; if unavailable stop and report, Pi decides next steps
- Emulator will show units as offline (different network segment) — expected, not a failure
- Infrastructure stack complete (I-001 through I-004 all ✅)

## Done (last 5)

| Task | Result |
|------|--------|
| ANDROID-004 | Config screen: Device + MQTT fields, GET load + POST save; APK ✅, analyze clean |
| ANDROID-003 | Live dashboard polling /api/data every 2s; per-phase V/A/W/Hz/PF/VAr + totals |
| ANDROID-002 | Unit list + nav skeleton; APK ✅, analyze clean |
| ANDROID-001 | Flutter 3.44.0 + Java 17.0.18 + Android SDK API 36 |
| I-004 | Power + Energy dashboards live at http://192.168.110.11:3000 |

## Next unlock

| Condition | Unlocks |
|-----------|---------|
| ANDROID-005 ✅ (KVM ok) | Future ANDROID tasks can include emulator screenshots as evidence |
| ANDROID-005 ✅ (no KVM) | Pi plans alternative test approach |

---

## Convention

- **Start of session:** read this file first — no need to load full task specs
- **Task done:** update this file + `tasks/INDEX.md` + write `setup/XXX.md` in one commit; set status to `Done — awaiting Pi review`
- **Pi review:** reads `setup/XXX.md`, fixes issues, updates status to `Ready` for next task
- **User handoff:** short message only — "ANDROID-005 ready", etc.

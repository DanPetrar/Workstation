# Current Status — ZaxEnergy Infrastructure

_Updated: 2026-05-27 by Pi Claude_

## Active tasks

| Task | Status | Assigned to |
|------|--------|-------------|
| I-004 | Ready | Workstation |

## Blocking / notes

- InfluxDB org is `zax` (not `zaxenergy`) — already corrected in all task specs
- Grafana admin password is still default `admin` — Step 0 of I-004 changes it
- Data source UID for Grafana queries: `ffnbf64waxe68a`
- Existing `zax-bridge` / `zax-influx` services on Workstation handle `zax/json/#` — unrelated, leave untouched

## Done (last 5)

| Task | Result |
|------|--------|
| I-003 | zax-parser.service active; Unit_A + Unit_C flowing into `power` + `energy` measurements |
| I-002 | Grafana 13.0.1, data source `ZaxEnergy-InfluxDB` (UID `ffnbf64waxe68a`), health OK |
| I-001 | InfluxDB v2.7.11, org `zax`, bucket `zaxenergy`, token in `setup/I-001-influxdb.md` |

## Next unlock

| Condition | Unlocks |
|-----------|---------|
| I-004 ✅ | ANDROID-001 (Flutter setup) can start in parallel |

---

## Convention

- **Start of session:** read this file first — no need to load full task specs
- **Task done:** update this file + `tasks/INDEX.md` + write `setup/I-XXX.md` in one commit; set status to `Done — awaiting Pi review`
- **Pi review:** reads `setup/I-XXX.md`, fixes issues, updates status to `Ready` for next task
- **User handoff:** short message only — "I-004 ready", etc.

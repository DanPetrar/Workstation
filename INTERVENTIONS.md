# Workstation interventions

Every change made to the live Workstation, newest last.

## 2026-09-03 11:21 — deploy W2 (exact-length dispatch) to zaxmodbus-parser

**What:** replaced `/opt/zaxmodbus-parser/zaxmodbus_parser.py` and restarted
`zaxmodbus-parser.service`. Backup: `zaxmodbus_parser.py.bak-20260903-112106`.
Repo source: `infrastructure/zaxmodbus_parser.py` (commit 6167f04).

**Why:** the parser tested `len(payload) < 28` / `< 76` — minimum lengths. The
1.2.0 MinRecord puts the import pair first so its 28 B prefix stays a valid
1.1.x record, so a `>= 28` test would accept a 52 B record, decode import
correctly and **silently discard the export pair**. Must ship before any unit
runs 1.2.0.

**Verified in production, not just by unit test.** The parser subscribes only to
the 15 fleet prefixes and none were publishing, so synthetic payloads were
published to `zax_E4A85C/min`:

| payload | result |
|---------|--------|
| 28 B | `kwh=111.1, kvarh=11.1` — no export fields written (absent, not zero) |
| 52 B | `kwh=444.4, kvarh=44.4, kwh_exp=777.7, kvarh_exp=77.7` |
| 16 B | `REJECT min from ZaxModbus-01: 16 B is not a known length (x1) — record dropped, not guessed` |

**Cleanup:** the synthetic points were deleted from the `zaxmodbus` bucket
(`/api/v2/delete`, HTTP 204, `_measurement="energy" AND unit="ZaxModbus-01"`,
08:43:30-08:44:05Z). Verified 0 rows remain.

**Rollback:** `sudo cp /opt/zaxmodbus-parser/zaxmodbus_parser.py.bak-20260903-112106 \
/opt/zaxmodbus-parser/zaxmodbus_parser.py && sudo systemctl restart zaxmodbus-parser`

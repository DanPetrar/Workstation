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

## 2026-09-03 11:50 — deploy W2 to zax-parser (the BENCH parser, missed by the first pass)

**What:** replaced `/opt/zax-parser/zax_parser.py` and restarted `zax-parser.service`.
Backup: `zax_parser.py.bak-20260903-11*`. Redeployed at 11:56 after adding a
`__main__` guard, so repo and deployment are byte-equivalent apart from the token.

**Why this was a hole in W2.** The first pass fixed only
`zaxmodbus_parser.py` (the 15 fleet prefixes). `zax_parser.py` serves
`zax_E47730`/`E482C0`/`73DA28`/`F07F8C` — **Unit_A..D, the bench units, which are
the first machines that will ever run 1.2.0**. It still had `len(payload) < 28`,
so it would have silently dropped the export pair exactly where 1.2.0 lands first.

**Token handling:** the repo copy keeps the `REPLACE_WITH_TOKEN_FROM_I-001`
placeholder by design; the live token is re-injected during deployment and never
committed. (It was printed once in a diff during this session — worth rotating.)

**Verified against live traffic, not synthetic:** Unit_A is on the box and
publishing, so after the restart real records flowed through the new code —
**9 `energy.kwh` points in 3 minutes, 0 rejects, 0 errors**, and `kwh_exp` = 0
points, correct because no unit runs 1.2.0 yet. That also demonstrates W3's
"tolerate a missing series": the export query returns nothing and nothing breaks.

**Rollback:** `sudo cp /opt/zax-parser/zax_parser.py.bak-20260903-11* \
/opt/zax-parser/zax_parser.py && sudo systemctl restart zax-parser`

## 2026-09-03 12:05 — deploy W1 + W4

**What:** `git pull` in `/home/dan-linux/Workstation` (the checkout the gap crons
run from, so W4 deploys by pull), then copied both parsers into `/opt/zax-parser/`
and `/opt/zaxmodbus-parser/` and restarted both services. Backups taken as
`*.bak-20260903-12*`; the live Influx token is re-injected into `zax_parser.py`
during deployment and never committed.

**W1 — implausible timestamps refused.** `zax_parser.py` had no timestamp
validation at all and wrote `ts * 1e9` straight through, so a unit with an unset
clock produced 1970 points — the most likely source of the pre-2020 rows already
in the bucket. Both parsers now enforce MIN_TS (2020-01-01) and reject anything
more than a day ahead. **Not the end state:** philosophy P2 wants such data
MARKED and kept, not dropped; the carrier is spec B19, still undecided.

**W4 — backfill follows `X-Zax-Next-From`.** It walked fixed 240 s slices and
never read the header, working only because sec records are 1 Hz and a 240 s
slice stays under the 400-row cap. Verified live on Unit_A: a 661 s window gives
400 rows + next_from in one request, 646 rows when followed — **246 rows a single
request would have lost.**

**Post-deploy health:** both services active, no rejects/errors in the first
2 minutes, and live bench traffic still being written.

**Rollback:** restore `*.bak-20260903-12*` over each parser and restart; for W4,
`git checkout` the previous commit in the ws checkout.

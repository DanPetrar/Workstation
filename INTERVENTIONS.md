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

## 2026-09-30 19:30 (EEST) — temporary LAN download of the boxlink 0.1.0 package (port 8090, auto-stops after 24 h)

**What:** copied `boxlink-0.1.0.tar.gz` and `boxlink-0.1.0.tar.gz.sha256` (from the raspi, `~/ZaxModbus/boxlink/package/out/`) to
`/home/dan-linux/boxlink-download/` on the Workstation and started a **transient** systemd unit
`boxlink-download.service` (`sudo systemd-run --unit=boxlink-download --property=RuntimeMaxSec=86400 --uid=dan-linux
python3 -m http.server 8090 --bind 192.168.20.11 --directory /home/dan-linux/boxlink-download`). No file under `/etc` or `/opt` was
touched, no permanent unit, nothing survives a reboot. Nothing existing was changed: `:8080` (`cal_reports`) is untouched.

**Why:** the owner personally hands the package to the box developer and wanted a download link inside the LAN:
`http://192.168.20.11:8090/boxlink-0.1.0.tar.gz` (checksum file next to it, directory listing shows only those two files).
Package sha256 `5c0421b818bbf351d65a929649b5bd88c02255f4309dadd5501c54ca7da6295e`. Source of truth: the private GitHub release
`boxlink-0.1.0` of `DanPetrar/ZaxModbus`.

**Exposure:** plain HTTP, no authentication, LAN only (ufw is inactive, so anything on 192.168.20.0/24 can fetch the two files).
The spec and the module are meant to leave the house anyway; nothing else is in that directory.

**Verified:** from the raspi, `curl` gets HTTP 200, the downloaded tarball passes `sha256sum -c`, `ss -ltn` shows only
`192.168.20.11:8090` for the unit, `systemctl show boxlink-download -p RuntimeMaxUSec` = 1d.

**Stop / extend / clean up:** the unit stops itself 24 h after 2026-09-30 19:30:34 EEST. Stop earlier: `sudo systemctl stop boxlink-download`.
Extend: `sudo systemctl stop boxlink-download` then run the same `systemd-run` command again. When no longer needed:
`rm -r /home/dan-linux/boxlink-download` (the files are copies, the release is the master).

## 2026-09-30 19:46 (EEST) — boxlink download link stopped

**What:** the package was handed over by the owner; `sudo systemctl stop boxlink-download` (the transient unit of the entry above). `:8090` no longer listens
(verified with `ss` and `curl`). The two copies stay in `/home/dan-linux/boxlink-download/` (harmless, no service points at them); remove with
`rm -r /home/dan-linux/boxlink-download` when wanted. The master is the private GitHub release `boxlink-0.1.0`.

## 2026-10-13 17:57 (EEST) — PS-Z001 (first new-hardware unit) added to zax-parser and to Grafana

**What:**
1. `/opt/zax-parser/zax_parser.py`: one entry added to `UNITS` — `"zax_E49218": "PS-Z001"` — and `zax-parser.service` restarted
   at 17:57:45. Backup: `zax_parser.py.bak-20261013-175745`. Repo source: `infrastructure/zax_parser.py` (same change; the deployed
   copy differs from the repo only in the InfluxDB token, as before).
2. Grafana `zax-power` (v15 -> v16): `PS-Z001` added to the custom `unit` variable (options were `Unit_A`, `Unit_C`). The repo copy
   `infrastructure/grafana-power-dashboard.json` was re-exported from the live dashboard with the documented command; it had been
   an older bare-dashboard file, so its diff is large and is not only this change.
3. Grafana `zax-energy` (v2 -> v3): the repo dashboard of commit `767a544` (W3: separate import and export targets on both panels)
   imported; it had been in the repo since 2026-09-03 but never imported. The live v2 was still the two-panel version provisioned
   by I-004 (compared before the import).
Backups of both live dashboards as returned by the API: `/home/dan-linux/grafana-backup-zax-power-20261013-175935.json`,
`/home/dan-linux/grafana-backup-zax-energy-20261013-175935.json`.

**Why:** PS-Z001 (NEW-BOX + S3-Zero, MAC `3C:0F:02:E4:92:18`, firmware 1.2.1, publishing `zax_E49218/sec` 76 B and `/min` 52 B to this
broker since 17:55) must be visible in Grafana so the owner can judge the validity of the new hardware's data.

**Effect on other units:** the parser restart took ~4 s; `/sec` and `/min` messages of Unit_A-D published in that window were not
written (QoS 0, no retry in the parser). No other service was touched.

**Verified:** journal shows `Subscribed to zax_E49218/#` and no `REJECT` line in the 3 minutes after; InfluxDB `zaxenergy`:
measurement `power`, `unit=PS-Z001`, 86 points per field in the first 86 s; measurement `energy` with `kwh`, `kvarh`, `kwh_exp`,
`kvarh_exp` per phase (20.218 / 20.224 / 27.944 kWh, 17.796 / 17.811 / 25.053 kvarh imported, 0 exported — the values the BOX sends).

**Undo:** restore the parser backup and restart `zax-parser`; re-post the two dashboard backups (`POST /api/dashboards/db` with
`overwrite: true`). Data already written for `unit=PS-Z001` stays in the bucket.

## 2026-10-13 18:11 (EEST) — PS-Z001 Grafana links on the web entry page (`:8080/zax`)

**What:** `/workspace/projects/EnergyCalibrator/reports/serve.py` (the `cal_reports` page server, `:8080`): one card added to the
ZaxEnergy page (`_zax_page()`), "New hardware -> Grafana", with two links — `zax-power/?var-unit=PS-Z001` and `zax-energy/`.
`cal_reports.service` restarted at 18:11:28. Backup: `serve.py.bak-20261013-181128` next to the file.

**Why:** owner's request: links to Grafana for PS-Z001 on the workstation web entry page.

**Not changed:** `ZAX_UNITS` (the four existing unit buttons), the other pages, `cal_collector` (the running calibration session's
collector is a separate service and was not restarted).

**State of that file in git:** `serve.py` was already modified and uncommitted in the WS clone of `EnergyCalibrator` before this
change (since 2026-08-01, with two older `.bak-*` files beside it); this edit adds to that uncommitted state, it was not committed.

**Verified:** `http://192.168.20.11:8080/zax` returns 200 from the raspi and shows the card with both links; `/` and `/zaxmodbus`
return 200.

**Undo:** copy the backup over `serve.py` and `sudo systemctl restart cal_reports`.

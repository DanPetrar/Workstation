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

## 2026-10-13 18:16 (EEST) — Grafana `zax-energy`: unit selector

**What:** `zax-energy` v3 -> v4: a dashboard variable `unit` (type query, values = the `unit` tag values that have `energy` data in
the last 30 days, with an "All" entry = `.*`, single selection, default All) and the filter `r.unit =~ /^${unit:raw}$/` added to
the four targets (import and export on both panels). Repo copy: `infrastructure/grafana-energy-dashboard.json`. Backup of the
live v3 as returned by the API: `/home/dan-linux/grafana-backup-zax-energy-20261013-181600.json`.
Also `serve.py` (`:8080/zax`): the PS-Z001 energy link now carries `?var-unit=PS-Z001`; `cal_reports` restarted again (18:17).

**Why:** owner's request: be able to show a single unit on the energy dashboard (it showed every unit together).

**Verified before saving:** the variable query returns `PS-Z001`, `Unit_A`, `Unit_B`; a panel query over 15 minutes returns 45 points
for `unit = PS-Z001` alone, and both PS-Z001 and Unit_B with `.*`. After saving: live v4 has the variable. Not checked in a browser.

**Undo:** re-post the v3 backup (`POST /api/dashboards/db`, `overwrite: true`).

## 2026-10-15 20:38-20:50 — Grafana `zax-power` v16 -> v18: energy table, injected + reactive energy, units, R/S/T legends

**What (owner `go`, review items M1 M2 E2 E4, `ZaxModbus/Doc/grafana/zax-power-review-20261015.md`):** via the Grafana API.
v17: units + decimals on the 6 power panels (V 1, A 2, W 0, Hz 2, PF 2 with -1..1, var 0), legend `${__field.labels.phase}`
on those and on "Active Energy per minute"; new panels at the bottom: 103 table "Energy in range" (R/S/T/total x kWh cons,
kvarh cons, kWh inj, kvarh inj; first difference taken from the last record before the range, like `hourly.py`), 104
"Injected Active Energy per minute (kWh)", 105 "Reactive Energy per minute (kvarh)" (legend "R consumed" ...).
v18: table column order (organize transformation). Existing panels otherwise unchanged.
**Backup:** `/home/dan-linux/grafana-backup-zax-power-20261015-203802.json` (v16); Grafana version history.
**Verified:** table query for PS-Z001 19:00-20:00 = hourly report total 0.018 / 0.042 / 0.009 / 0.082 and per phase;
`/api/ds/query` last hour: power panels 3 frames labelled R/S/T, table 4 rows, kvarh panel 6 frames (phase x dir), no errors.
Repo export `infrastructure/grafana-power-dashboard.json` updated to v18.

## 2026-10-15 20:54-20:56 — Grafana `zax-power` v18 -> v19 (owner's layout, owner `go`)

Injected row directly under the consumed row: 104 "Injected Active Energy per minute (kWh)" (now the same query as panel
100 on `kwh_exp`) + new stat 106 "Injected Active Energy (kWh)" (copy of 101 on `kwh_exp`). Owner: no reactive energy in
this dashboard -> panel 105 deleted, "Energy in range" reduced to Phase / kWh consumed / kWh injected ("Reactive Power
(VAr)" panel kept: power, not energy). Panels below moved down 8 rows. Backup `/home/dan-linux/grafana-backup-zax-power-
20261015-205448.json` (v18). Verified: no `kvarh` in the dashboard; PS-Z001 19:00-20:00 stat injected T 0.009 / Total
0.009, table kWh 0.018 / 0.009 = hourly report; `/api/ds/query` last hour: 104 3 frames, 106 4 values, 103 4 rows, no errors.

## 2026-10-21 16:43 (EEST) — zax-parser: `ts = 0` accepted (new hardware, time-spec T4; owner `go`)

**What:** `/opt/zax-parser/zax_parser.py` replaced by the repo file of commit `404896a` (token re-injected from the previous deployed copy, never printed
or committed) and `zax-parser.service` restarted 16:43:49. A record with `ts = 0` is now written at its arrival time with the field `async=1i`
(SEC `power` and MIN `energy` points); `1 <= ts < 2020-01-01` and far-future `ts` are still refused. Timed records are unchanged. The fleet parser
`zaxmodbus_parser.py` is untouched. Reason: the firmware of the new hardware will send `ts = 0` while it has no real time (D2); this parser had to
accept it first.
**Backup:** `/opt/zax-parser/zax_parser.py.bak-20261021-164349`. **Rollback:** `sudo cp /opt/zax-parser/zax_parser.py.bak-20261021-164349
/opt/zax-parser/zax_parser.py && sudo systemctl restart zax-parser`.
**Verified:** deployed file minus the token line = repo file; service active; journal: Connected, Subscribed to the 5 unit prefixes, no error in 60 s.
**Not verified:** a real `ts = 0` record in InfluxDB (needs PS-Z001 running the firmware that sends it: time-spec step 3). `ws` git checkout not pulled.

## 2026-10-21 18:54 (EEST) — zax-parser: `ts = 0` points at arrival time in ns (owner `go`)

**What:** `/opt/zax-parser/zax_parser.py` replaced by the repo file of commit `00f01fd` (token re-injected from the previous deployed copy, never printed or
committed) and `zax-parser.service` restarted 18:54:12. A `ts = 0` record (new hardware, no real time) is written at its arrival time in **nanoseconds**,
strictly increasing (`max(time_ns, last + 1)`); until now the arrival time was whole seconds, so records of one second overwrote each other (a replay batch of
200 would have collapsed to about one point). The `async=1i` mark, timed records and the fleet parser `zaxmodbus_parser.py` are unchanged.
**Backup:** `/opt/zax-parser/zax_parser.py.bak-20261021-185412`. **Rollback:** `sudo cp /opt/zax-parser/zax_parser.py.bak-20261021-185412
/opt/zax-parser/zax_parser.py && sudo systemctl restart zax-parser`.
**Verified:** deployed file minus the token line = repo file; service active; journal: Connected, Subscribed to the 5 unit prefixes, no error in 70 s.
**Not verified:** a real `ts = 0` point in InfluxDB (needs PS-Z001 running the 1.2.14 firmware: time-spec step 3). `ws` git checkout not pulled.

## 2026-10-28 17:52 (EET) — temporary LAN page 8091 again, for the PS-E002 grid run (auto-stops after 20 h)

**What:** the transient unit of 2026-10-23 (below) had stopped by its 5-day limit (state failed). `sudo systemctl reset-failed
psz001-status`, then the same `systemd-run --unit=psz001-status ... python3 -m http.server 8091 --bind 192.168.20.11
--directory /home/dan-linux/psz001-status` with `--property=RuntimeMaxSec=72000` (20 h, stops ~Thu 2026-10-29 13:52). Active
17:52:53, `http://192.168.20.11:8091/` 200. Nothing else changed; no file under `/etc`.
**Why:** owner 2026-10-28 "monitor the unit until tomorrow 8:00 and view hourly results on the workstation web page" (`go`):
`soak_run --publish` of the PS-E002 grid run copies `index.html` there after each judged hour (page title still says PS-Z001,
WISHLIST #95).
**Undo:** `sudo systemctl stop psz001-status` (or wait for the 20 h).

## 2026-10-23 15:14 (EEST) — temporary LAN page for the PS-Z001 weekend runs (port 8091, auto-stops after 5 days)

**What:** directory `/home/dan-linux/psz001-status/` created and a **transient** systemd unit `psz001-status.service` started
(`sudo systemd-run --unit=psz001-status --property=RuntimeMaxSec=432000 --uid=dan-linux python3 -m http.server 8091 --bind
192.168.20.11 --directory /home/dan-linux/psz001-status`). No file under `/etc` or `/opt` was touched, no permanent unit,
nothing survives a reboot. Nothing existing was changed: `:8080` (`cal_reports`) is untouched.

**Why:** owner 2026-10-23: "show each hour an overview report for current status" of the weekend soak runs. The raspi
(`ZaxModbus-PS/tools/zaxtest/soak_overview.py`, called by `soak_run --publish` after each judged hour) copies
`<run>.html` and `index.html` there with `scp`. Page: `http://192.168.20.11:8091/`.

**Undo:** `sudo systemctl stop psz001-status` (or wait for the 5 days), then `rm -r /home/dan-linux/psz001-status`.

## 2026-10-27 17:34 (EET) — PS-E002 (NEW-BOX + S3-ETH) added to zax-parser and to Grafana `zax-power` (owner `now`)

**What:**
1. `/opt/zax-parser/zax_parser.py`: one entry added to `UNITS` — `"zax_849DEC": "PS-E002"` — and `zax-parser.service` restarted
   at 17:34:01.99. Backup: `zax_parser.py.bak-20261027-173401`. Repo source `infrastructure/zax_parser.py`: same change (deployed
   copy = repo except the InfluxDB token, checked by diff). A `py_compile` check created `/opt/zax-parser/__pycache__/`; removed.
2. Grafana `zax-power` (v19 -> v20): `PS-E002` added to the custom `unit` variable (via the API). Backup as returned by the API:
   `/home/dan-linux/grafana-backup-zax-power-20261027-173442.json`. Repo copy re-exported with the documented command (this
   also drops `id` and writes the title's dash as `—`).

**Why:** PS-E002 (MAC STA `E8:F6:0A:84:9D:EC`, ETH `EE:F6:0A:84:9D:ED`, fw 1.2.16, topic `zax_849DEC`) is on the bench since
2026-10-27 with the BOX link running; its data must be visible in Grafana.

**Effect on other units:** the parser restart (~4 s) drops `/sec` and `/min` of every unit in that window (QoS 0, no retry). The
PS-Z001 fault-1 grid run (`ZaxModbus-PS/Doc/new-hardware/PS-Z001/grid-20261027/`) counts PS-Z001 seconds per hour from Influx:
its hour 17:00-18:00 is expected below 3599 because of this restart (owner chose `now` knowing this).

**Verified:** journal `Subscribed to zax_849DEC/#` at 17:34:02; Influx `zaxenergy` `power` `unit=PS-E002`: 81 points per field in
the first ~90 s; Grafana `unit` options Unit_A, Unit_C, PS-Z001, PS-E002.

**Undo:** restore the parser backup and restart `zax-parser`; re-post the dashboard backup (`POST /api/dashboards/db` with
`overwrite: true`).

## 2026-10-27 19:42 (EET) — `:8080/zax` "New hardware" card: one list for all new units, PS-E002 added (owner `go`)

**What:** `/workspace/projects/EnergyCalibrator/reports/serve.py` (`cal_reports`): `NEW_UNITS = ['PS-Z001', 'PS-E002']` added
beside `ZAX_UNITS`; the "New hardware -> Grafana" card of `_zax_page()` now builds one Power (`zax-power/?var-unit=<u>`) and one
Energy (`zax-energy/?var-unit=<u>`) button per unit from that list, instead of the two hand-written PS-Z001 links of 2026-10-13
18:11/18:17. A new unit = one name in `NEW_UNITS`. `cal_reports.service` restarted at 19:42:48. Backup:
`serve.py.bak-20261027-194248` next to the file.

**Why:** owner: PS-E002 in the workstation page's new-hardware selection like PS-Z001, unified so any unit can be selected. The
17:34 entry above (parser + `zax-power`) missed this page: the 2026-10-13 18:11 entry was not read when planning it.

**Not changed:** `ZAX_UNITS`, the other pages, `cal_collector` (still active). As on 2026-10-13, `serve.py` stays uncommitted in
the WS clone of `EnergyCalibrator` (already modified since 2026-08-01).

**Verified:** `/zax`, `/` and `/zaxmodbus` return 200 from the raspi; `/zax` shows PS-Z001 and PS-E002, each with Power and
Energy (import / export) links carrying `?var-unit=<unit>`.

**Undo:** copy `serve.py.bak-20261027-194248` over `serve.py` and `sudo systemctl restart cal_reports`.

## 2026-10-27 19:49 (EET) — one link per dashboard; Power unit list from Influx, as Energy (owner `go`)

**What:**
1. Grafana `zax-power` (v20 -> v21): the `unit` variable is now the same kind as on `zax-energy` — type query, values = the
   `unit` tag values with `power` data in the last 30 days, refreshed on dashboard load, single selection, no "All" (the Power
   panels filter `r.unit == "${unit}"`). Today: PS-E002, PS-Z001, Unit_B (Unit_A, Unit_C left the list: no `power` data in
   `zaxenergy` in 30 days). Backup: `/home/dan-linux/grafana-backup-zax-power-20261027-194935.json`. Repo copy re-exported.
2. `serve.py` (`:8080/zax`): one card "Grafana" with two links, Power and Energy, without a unit; the unit is chosen in the
   dashboard. Removed: the Unit_A-D buttons (`ZAX_UNITS`), the New hardware card and `NEW_UNITS` (19:42 entry above).
   The `.chart-btn` style of that page is left in place, unused. `cal_reports` restarted 19:50:07. Backup:
   `serve.py.bak-20261027-195007`. Still uncommitted in the WS clone of `EnergyCalibrator`, as before.

**Why:** owner: keep a single link to Power and to Energy and select the unit in Grafana; a new unit then appears in both
dashboards by itself (no parser-side or page edit needed beyond the zax-parser `UNITS` entry).

**Verified:** Grafana datasource query of the new variable returns PS-E002, PS-Z001, Unit_B; `/zax`, `/`, `/zaxmodbus` 200;
`/zax` shows the two links; `cal_collector` still active.

**Undo:** re-post the dashboard backup (`POST /api/dashboards/db`, `overwrite: true`); copy `serve.py.bak-20261027-195007`
(or `-194248` for the 19:42 state) over `serve.py` and `sudo systemctl restart cal_reports`.

# Infrastructure — Source of Truth

_Single authoritative map of **what runs where**, the **data-flow / broker map**, the
**operating rules**, and **per-service deploy steps**. Maintained by Pi Claude. When a
service is added, moved, or removed, update this file in the same commit._

_Last verified live: 2026-08-06 (Pi Claude, via `ssh ws`)._

> Status snapshots and migration history live in [`STATUS.md`](STATUS.md); installed
> tool versions in [`inventory.md`](inventory.md); the session-handoff workflow in
> [`COORDINATION.md`](COORDINATION.md). **This file is the steady-state runtime map.**

---

## 1. What runs where

### Pi — `192.168.20.225` (Raspberry Pi, Debian)

Role: **serial-attached prototyping, Arduino build/flash, dev MQTT broker.** (Coordinator
role is being transferred to futro — see `Workspace/nodes/INDEX.md` and
`nodes/futro/setup-plan.md` for handoff status.)

| Service | Purpose | Listen / target | Enabled |
|---------|---------|-----------------|---------|
| `mosquitto.service` | Local dev/test-only broker — **no production publisher or subscriber uses it** (verified 2026-08-06: zero connected clients, ZAX fleet has published directly to the Workstation broker since 2026-06-24) | `:1883` | ✅ |
| `zax_directory.service` | ZaxEnergy unit directory | — | ✅ |

No bench services on the Pi — the EnergyCalibrator bench was migrated to the
Workstation (2026-06-02) and the Pi bench crons removed. Arduino toolchain +
`arduino_upload.sh` / `build_lilygo.sh` stay on the Pi (USB serial). Pi crontab: one
entry, `00:15` daily `rsync boards.json` to `/workspace/backups/boards-json/` on the
Workstation (disaster-recovery backup, added 2026-08-06 — see
`Workspace/nodes/futro/setup-plan.md` on why this file matters).

### Workstation — `192.168.20.11` (`MainDevbox`, Ubuntu 26.04, `/workspace` 207 GB free)

Role: **all permanent / production services.** Driven from the Pi via `ssh ws`.

| Service | Purpose | Listen / target | Enabled |
|---------|---------|-----------------|---------|
| `mosquitto.service` | Permanent broker — all ZAX fleet units (A/B/C/D) **and** the EnergyCalibrator bench publish here | `:1883` | ✅ |
| `chrony` | NTP server for the bench-LAN dev range — local backup time source since `pool.ntp.org` is unreliable there even though the Workstation's own upstream sync is fine (Canonical NTS pool, stratum 3). Config: `allow 192.168.20.64/26` + `allow 192.168.20.128/25` in `/etc/chrony/conf.d/bench-lan-server.conf` (source tracked at `infrastructure/bench-lan-server.conf`). Added 2026-08-06, verified with a real cross-host UDP-123 query (in-range client got a reply, `.11` itself queried as an external client was correctly refused). | `:123` (UDP) | ✅ |
| `influxdb.service` | Time-series DB — org `zax`, bucket `zaxenergy` | `:8086` | ✅ |
| `grafana-server.service` | Dashboards | `:3000` (admin `zaxenergy2026`) | ✅ |
| `zax-parser.service` | **LIVE** ZAX A/B/C/D path: subscribes **local** broker (`localhost:1883`) — `zax_E47730/#`, `zax_E482C0/#`, `zax_73DA28/#`, `zax_F07F8C/#` — binary → InfluxDB | — | ✅ |
| `cal_collector.service` | Bench: subscribes **local** broker `cal_F07F8C/#` → SQLite `cal_data.db` | — | ✅ |
| `cal_reports.service` | Bench report web server **+ session UI** (start/stop/report by DUT serial — EnergyCalibrator Phase E) | `:8080` | ✅ |
| `cal-parser.service` | Bench: subscribes **local** broker `cal_F07F8C/#` → InfluxDB | — | ✅ |
| `zax-bridge.service` | Disabled 2026-06-03 — see note below | local broker `zax`→`zax/json` | ❌ disabled |
| `zax-influx.service` | Disabled 2026-06-03 — see note below | local broker `zax/json` → InfluxDB | ❌ disabled |

> **No Pi-relay hop.** Prior to 2026-06-24 the ZAX fleet published to a Pi-hosted broker
> that `zax-parser` remote-subscribed. That hop was removed and every unit now publishes
> `mqtt_host` pointed directly at the Workstation — confirmed still true 2026-08-06. See
> section 2 for the corrected data-flow diagram. Note `zax_F07F8C` (Unit_D, ZaxModbus
> fleet) and the bench's `cal_F07F8C` topic are the **same physical board** (MAC suffix
> `F07F8C`), repurposed from its earlier EnergyCalibrator-bench role — not a naming
> collision between two different units.

> **Disabled ZAX JSON pipeline (`zax-bridge` + `zax-influx`).** These listened on the
> **local** WS broker (topics `zax` / `zax/json`), which nothing publishes to — ZAX units
> publish to the **Pi** broker and there is **no mosquitto bridge** between the two brokers,
> so the pair processed no messages (no log activity from startup 2026-05-27 to disable).
> They were an older JSON-relay design superseded by `zax-parser` (the sole live A/C →
> InfluxDB path). **Disabled + stopped 2026-06-03** (`sudo systemctl disable --now
> zax-bridge zax-influx`). Source remains at the path in section 4 if the local-broker
> JSON feed is ever wanted again.

### Units (publishers)

| Unit | IP | MQTT prefix | Publishes to |
|------|----|-------------|--------------|
| Unit_A | 192.168.20.231 (reserved) | `zax_E47730` | WS broker `.11` |
| Unit_B | 192.168.20.232 (reserved) | `zax_E482C0` | WS broker `.11` |
| Unit_C | 192.168.20.233 (reserved) | `zax_73DA28` | WS broker `.11` |
| Unit_D | 192.168.20.234 (reserved) | `zax_F07F8C` / `cal_F07F8C` | WS broker `.11` (see note above — dual role) |

---

## 2. Data-flow / broker map

```
ZAX FLEET UNITS (A / B / C / D)                BENCH (Unit_D, cal_F07F8C)
   zax_E47730 / zax_E482C0 /                      box CTs + SDM630 ref meter
   zax_73DA28 / zax_F07F8C                                    |
            |                                                |
            | MQTT (binary 76B sec / 28B min)                | MQTT (76B sec / JSON min)
            v                                                v
                 WS broker  mosquitto :1883  (192.168.20.11)
            |                                          |                    |
            v                                          v                    v
   WS: zax-parser (localhost)       WS: cal_collector (localhost)   WS: cal-parser (localhost)
                                  |              |                         |
                                  |          SQLite cal_data.db            |
                                  |          (/workspace/cal-data/)        |
                                  |              |                         |
                                  v              v                         v
                       InfluxDB :8086  <----  cal_reports :8080      InfluxDB :8086
                       (org zax, bucket          (PDF / web)         (power, cal_meter,
                        zaxenergy)                                    cal_box, cal_dev)
                                  |                                         |
                                  +--------------> Grafana :3000 <----------+
                                  ("ZaxEnergy" dashboards)   ("Bench - calibration" uid bench-calib)

   (disabled 2026-06-03: zax-bridge -> zax/json -> zax-influx; local broker, no publisher)
```

- **ZAX path:** units → Workstation broker directly → `zax-parser` (localhost-subscribed,
  no relay hop) → InfluxDB → Grafana. No Pi broker involvement since 2026-06-24.
- **Bench path:** Unit_D → WS broker → `cal_collector` (→ SQLite → `cal_reports` PDF/web) **and** `cal-parser` (→ InfluxDB → Grafana).
- WS broker is anonymous on `:1883` and is the **sole production broker** for both paths.
  Pi's own broker (also anonymous, `:1883`) is local dev/test-only — see section 1.

---

## 3. Operating rules

These are the standing rules for where new work goes (Phase D / migration outcome):

1. **New permanent / production service → the Workstation**, installed via direct SSH
   from the Pi session (`ssh ws`, key-based, passwordless sudo). Add it to **section 1**
   of this file in the same commit, and to its health script (`infrastructure/health-ws.sh`).
2. **New prototype / in-development / serial-attached work → the Pi.** Anything that
   needs USB serial or is still being iterated stays local until it's permanent.
3. **Firmware build & flash always stay on the Pi** (Arduino toolchain + USB serial:
   `arduino_upload.sh`, `build_lilygo.sh`). The Workstation has no board attached.
4. **Brokers:** the WS broker is the sole production broker (bench + all ZAX fleet
   units). Pi's broker is local dev/test-only — don't add production publishers to it.
5. **Data-safety for any future cutover:** parallel-run → verify both stores agree →
   switch publisher → decommission old path. Never tear down the old path first.
6. **Driving the Workstation:** `ssh ws` is the default. The GitHub task-spec hand-off
   (see [`COORDINATION.md`](COORDINATION.md)) is the fallback for work that must run in a
   Claude session *on* the Workstation. Don't ask the (non-Linux) user to run git/ssh by hand.
7. **The Workstation is the infrastructure's primary data server** — InfluxDB, the
   production broker, Grafana, the bench SQLite DB and the flat-file error-log archive
   all live here, and most of it exists nowhere else. Treat every change to it as a
   change to shared state, not to a personal machine.
8. **Every intervention on the Workstation must be documented, in the same session it is
   made.** A change that is not written down did not happen, because the next session
   cannot see it. Where it goes:
   - a new or changed service, cron, or scheduled task → **section 1** and **section 4**
     of this file, in the same commit as the change;
   - anything installed, deployed, or configured outside git (`/opt`, systemd units,
     package installs, credentials) → note it here with its on-disk path, since the repo
     is otherwise not a complete record of the machine;
   - an incident, a surprising diagnosis, or a fix whose reasoning matters →
     [`errors-history.md`](errors-history.md);
   - a bench event that changes what stored data means (a reflash, a repartition, a wipe)
     → a marker in the affected data itself, not only in prose.
   Scripts deployed here belong **in this repo**, and this clone must be kept current:
   `zax_errorlog_watch.py` was committed and documented from another session on
   2026-08-26 (`8d2b645`), but the WS clone was never pulled, so local `git status`
   showed it untracked and the local doc lacked its entry — a change can look missing
   here purely because this working copy is behind `origin`. **Run `git pull` on this
   repo before concluding anything is undocumented, and before starting WS work.**
9. **Claude performs all Workstation interventions for now.** The user does not operate
   this machine directly, so there is no second person who will notice an undocumented
   change or reconstruct intent from memory. Assume the record is the only handover.

---

## 4. Per-service deploy / operate

All WS Python services run from the EnergyCalibrator venv unless noted:
`/workspace/projects/EnergyCalibrator/.venv/bin/python3` (paho-mqtt, reportlab,
influxdb-client). The ZAX services use their own venv at
`/workspace/projects/mixed/ZaxEnergySurvey/collector/.venv/`.

| Service | Unit file / source | Restart | DB / output |
|---------|--------------------|---------|-------------|
| `cal_collector` | source `/workspace/projects/EnergyCalibrator/collector/cal_collector.py`; env `CAL_DB`, `CAL_MQTT_HOST=127.0.0.1` | `ssh ws sudo systemctl restart cal_collector` | SQLite `/workspace/cal-data/cal_data.db` |
| `cal_reports` | source `/workspace/projects/EnergyCalibrator/reports/serve.py`; serves `:8080` (PDF index + session UI; `sessions` table in `cal_data.db`) | `… restart cal_reports` | PDF/web + session reports from `cal_data.db` |
| `cal-parser` | runs `/opt/cal-parser/cal_parser.py` (source tracked at `infrastructure/cal_parser.py`); broker `127.0.0.1` | `… restart cal-parser` | InfluxDB bucket `zaxenergy` |
| `zax-parser` | runs `/opt/zax-parser/zax_parser.py`; broker `localhost` (source tracked at `infrastructure/zax_parser.py` — kept in sync with the deployed copy) | `… restart zax-parser` | InfluxDB bucket `zaxenergy` |
| `zax-bridge` / `zax-influx` | `/workspace/projects/mixed/ZaxEnergySurvey/collector/{bridge,influx_writer}.py` (disabled 2026-06-03) | — | — |

**Scheduled tasks (WS, `dan-linux` crontab)** — `ssh ws crontab -l` is the authority for
*what* is scheduled; this table exists to say *why*, so an unfamiliar line in `ps` or a
mystery file on disk can be traced back in one look. Keep it in step with the crontab.

| Schedule | Task | Why it exists | Writes to |
|----------|------|---------------|-----------|
| `00:05` daily | `/workspace/cal-data/ws_daily_report.sh` | EnergyCalibrator bench daily PDF report | `/workspace/cal-data/` |
| `00:30` Mon–Sat | `prune.py --apply` | 10-day retention on the bench SQLite DB, or it grows without bound | `/workspace/cal-data/prune.log` |
| `00:30` Sun | `prune.py --apply --vacuum` | Weekly variant — same prune, plus reclaims file space (VACUUM is too slow to run daily) | `/workspace/cal-data/prune.log` |
| every 5 min | `infrastructure/zax_gap_watch.py` | Gap **detection**: finds holes in bench time-series in InfluxDB and records them as the `data_gap` measurement, so an outage is visible as data rather than as absence. **Bench units only, not the delivered fleet.** Watches the `power` measurement only — an energy-only hole is not detected. | `infrastructure/zax_gap.log` |
| every 15 min (:07,:22,:37,:52) | `infrastructure/zax_gap_backfill.py` | Gap **recovery**: for each non-recovered `data_gap`, pulls the range from the device's own `/api/export` and writes the missing seconds/minutes back with `source=buffer_backfill`. **Restored 2026-09-01 after being absent since the 2026-08-05 incident** — detection had been running without recovery for ~4 weeks, which looks covered and is not. Pulls are CHUNKED (240 s per request): a single wide pull blocks the device's `loop()`, and therefore its box-serial read, long enough to trip its 10 s comm-loss fault. Needs the venv interpreter for `influxdb_client`. | `infrastructure/zax_gap.log` |
| hourly `:00` | `infrastructure/zax_errorlog_watch.py` (added 2026-08-26) | Flat-file archive of each unit's on-device error log. `/api/errors` is a small rotating buffer (~8% of LittleFS) that drops its oldest half when full; this fetches hourly and appends **only new lines**, giving unbounded local retention of a log the device itself cannot keep. | `infrastructure/errorlogs/<Unit>.log` (data), `infrastructure/zax_errorlog_watch.log` (run log) |

Two things about the error-log archiver that are easy to misread later:

- Its `UNITS` dict at the top of the script is the whole subscription list — currently
  **`Unit_B` only**. A unit absent from that dict is silently not archived; there is no
  warning anywhere.
- It finds where to resume by matching the **last line of the saved file** against the
  fresh fetch. If the device log was wiped (reflash, repartition, NVS clear) rather than
  merely rotated, that match fails and it writes a
  `[WATCHER] --- gap: ... boundary unknown ---` line and appends everything. The line is
  correct that a boundary occurred but names rotation as the cause, which may not be true
  — check for a nearby `[BENCH]` marker before believing it. Bench events are recorded
  by appending a `[BENCH]` line by hand (see `errorlogs/Unit_B.log`, 2026-08-29
  repartition).

**What ran, and did it work:**
```
ssh ws 'crontab -l'                                              # what is scheduled
ssh ws 'tail -5 ~/Workstation/infrastructure/zax_errorlog_watch.log'   # last hourly runs
ssh ws 'tail -5 ~/Workstation/infrastructure/zax_gap.log'              # last 5-min runs
ssh ws 'grep CRON /var/log/syslog | tail -20'                    # cron actually firing
```

**Bench DB:** `cal_sec(ts, unit, R_*/S_*/T_*)`, `cal_min(… deviation cols)`,
`cal_sec_hourly`. No `sqlite3` CLI on the WS — query via the venv python's `sqlite3`
module.

**Grafana dashboards (repo-tracked):** each dashboard is committed as an import-ready
`{folderUid, dashboard, overwrite}` JSON under `infrastructure/`:
- `grafana-bench-calibration-dashboard.json` — "Bench - calibration" (uid `bench-calib`):
  power vs SDM, deviation %, hourly energy deviation, cumulative energy, SDM stat.
- `grafana-power-dashboard.json`, `grafana-energy-dashboard.json` — ZaxEnergy dashboards.

Restore/import a dashboard:
```
curl -u admin:zaxenergy2026 -H "Content-Type: application/json" \
  -X POST http://localhost:3000/api/dashboards/db \
  -d @infrastructure/<file>.json
```

> **Password reset (if needed):** Must stop Grafana first, then use CLI, then start:
> ```
> sudo systemctl stop grafana-server
> sudo grafana cli --homepath /usr/share/grafana admin reset-admin-password zaxenergy2026
> sudo systemctl start grafana-server
> ```
⚠️ **Manual export** — editing a dashboard in the Grafana UI does **not** update the
repo copy. After UI changes, re-export to keep them in sync:
```
curl -s -u admin:zaxenergy2026 http://localhost:3000/api/dashboards/uid/<uid> \
  | python3 -c 'import json,sys; g=json.load(sys.stdin); d=g["dashboard"]; d.pop("id",None); \
json.dump({"folderUid":g["meta"].get("folderUid",""),"dashboard":d,"overwrite":True}, \
open("infrastructure/<file>.json","w"), indent=2)'
```

---

## 5. Health checks

Two per-machine scripts under [`infrastructure/`](infrastructure/), each run **locally**
on its own machine (so a check still works if `ssh ws` is down):

- **Pi:** `bash infrastructure/health-pi.sh` — broker `:1883`, `mosquitto` +
  `zax_directory` active, disk free.
- **Workstation:** `ssh ws 'bash …/Workstation/infrastructure/health-ws.sh'` (or run it
  locally on the WS) — core services active, broker `:1883`, **bench collector lag**
  (newest `cal_sec` row vs now), disk free for `/` and `/workspace`.

Each prints one `PASS` / `WARN` / `FAIL` line per check and exits non-zero if any check
fails. Run at the start of a session.

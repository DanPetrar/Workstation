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

**Crons (WS, `dan-linux` crontab):**
- `00:05` daily — `/workspace/cal-data/ws_daily_report.sh` (bench daily PDF)
- `00:30` Mon–Sat — `prune.py --apply` (retention 10 days)
- `00:30` Sun — `prune.py --apply --vacuum`

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

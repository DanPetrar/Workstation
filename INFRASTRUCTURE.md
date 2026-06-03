# Infrastructure — Source of Truth

_Single authoritative map of **what runs where**, the **data-flow / broker map**, the
**operating rules**, and **per-service deploy steps**. Maintained by Pi Claude. When a
service is added, moved, or removed, update this file in the same commit._

_Last verified live: 2026-06-03 (Pi Claude, via `ssh ws`)._

> Status snapshots and migration history live in [`STATUS.md`](STATUS.md); installed
> tool versions in [`inventory.md`](inventory.md); the session-handoff workflow in
> [`COORDINATION.md`](COORDINATION.md). **This file is the steady-state runtime map.**

---

## 1. What runs where

### Pi — `192.168.110.225` (Raspberry Pi, Debian)

Role: **serial-attached prototyping, Arduino build/flash, coordinator, dev MQTT broker.**

| Service | Purpose | Listen / target | Enabled |
|---------|---------|-----------------|---------|
| `mosquitto.service` | MQTT broker for ZAX field units (A/C) | `:1883` | ✅ |
| `zax_directory.service` | ZaxEnergy unit directory | — | ✅ |

No bench services and **no Pi crontab** — the EnergyCalibrator bench was migrated to
the Workstation (2026-06-02) and the Pi bench crons removed. Arduino toolchain +
`arduino_upload.sh` / `build_lilygo.sh` stay on the Pi (USB serial).

### Workstation — `192.168.110.11` (`MainDevbox`, Ubuntu 26.04, `/workspace` 207 GB free)

Role: **all permanent / production services.** Driven from the Pi via `ssh ws`.

| Service | Purpose | Listen / target | Enabled |
|---------|---------|-----------------|---------|
| `mosquitto.service` | Permanent broker — **Unit D (bench)** publishes here | `:1883` | ✅ |
| `influxdb.service` | Time-series DB — org `zax`, bucket `zaxenergy` | `:8086` | ✅ |
| `grafana-server.service` | Dashboards | `:3000` (admin `zaxenergy2026`) | ✅ |
| `zax-parser.service` | **LIVE** ZAX A/C path: subscribes **Pi** broker `.225` (`zax_E47730/#`, `zax_73DA28/#`), binary → InfluxDB | — | ✅ |
| `cal_collector.service` | Bench: subscribes **local** broker `cal_F07F8C/#` → SQLite `cal_data.db` | — | ✅ |
| `cal_reports.service` | Bench report web server | `:8080` | ✅ |
| `cal-parser.service` | Bench: subscribes **local** broker `cal_F07F8C/#` → InfluxDB | — | ✅ |
| `zax-bridge.service` | Disabled 2026-06-03 — see note below | local broker `zax`→`zax/json` | ❌ disabled |
| `zax-influx.service` | Disabled 2026-06-03 — see note below | local broker `zax/json` → InfluxDB | ❌ disabled |

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
| Unit A | 192.168.110.152 | `zax_E47730` | Pi broker `.225` |
| Unit C | 192.168.110.125 | `zax_73DA28` | Pi broker `.225` |
| Unit B | 192.168.110.76 | `zax_3C3C3C` | Pi broker `.225` (field, user-managed, may be offline) |
| Unit D (bench) | 192.168.110.104 | `cal_F07F8C` | **WS broker `.11`** (re-pointed 2026-06-02) |

---

## 2. Data-flow / broker map

```
ZAX FIELD UNITS (A / C / B)                    BENCH (Unit D, cal_F07F8C)
   zax_E47730 / zax_73DA28                         box CTs + SDM630 ref meter
            |                                                |
            | MQTT (binary 76B sec / 28B min)                | MQTT (76B sec / JSON min)
            v                                                v
   Pi broker  mosquitto :1883  (192.168.110.225)    WS broker  mosquitto :1883  (192.168.110.11)
            |                                          |                    |
            | (subscribed remotely)                    |                    |
            v                                          v                    v
   WS: zax-parser ----------------+         WS: cal_collector       WS: cal-parser
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

- **ZAX path:** units → Pi broker → `zax-parser` (on WS, remote-subscribed) → InfluxDB → Grafana.
- **Bench path:** Unit D → WS broker → `cal_collector` (→ SQLite → `cal_reports` PDF/web) **and** `cal-parser` (→ InfluxDB → Grafana).
- Both brokers anonymous on `:1883`. Pi broker stays up **only** for ZAX field units.

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
4. **Brokers:** the WS broker is the permanent one (bench + any new units). The Pi
   broker exists **only** for the legacy ZAX field units (A/C/B) until they migrate.
   Don't add new publishers to the Pi broker.
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
| `cal_reports` | source `/workspace/projects/EnergyCalibrator/reports/`; serves `:8080` | `… restart cal_reports` | PDF/web from `cal_data.db` |
| `cal-parser` | runs `/opt/cal-parser/cal_parser.py` (source tracked at `infrastructure/cal_parser.py`); broker `127.0.0.1` | `… restart cal-parser` | InfluxDB bucket `zaxenergy` |
| `zax-parser` | runs `/opt/zax-parser/zax_parser.py`; broker hard-set `192.168.110.225` | `… restart zax-parser` | InfluxDB bucket `zaxenergy` |
| `zax-bridge` / `zax-influx` | `/workspace/projects/mixed/ZaxEnergySurvey/collector/{bridge,influx_writer}.py` (disabled 2026-06-03) | — | — |

**Crons (WS, `dan-linux` crontab):**
- `00:05` daily — `/workspace/cal-data/ws_daily_report.sh` (bench daily PDF)
- `00:30` Mon–Sat — `prune.py --apply` (retention 10 days)
- `00:30` Sun — `prune.py --apply --vacuum`

**Bench DB:** `cal_sec(ts, unit, R_*/S_*/T_*)`, `cal_min(… deviation cols)`,
`cal_sec_hourly`. No `sqlite3` CLI on the WS — query via the venv python's `sqlite3`
module.

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

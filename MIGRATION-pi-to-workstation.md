# Runbook — Migrate Permanent Services Pi → Workstation

_Prepared 2026-06-01 (Pi Claude). **Execution begins 2026-06-02.** Do not run any
step until the Pending Decisions below are confirmed at the start of execution._

---

## 1. Purpose & goals

Move **permanent/production** services off the Raspberry Pi onto the **I3
Workstation**, so that:

1. **Direct control** — the Pi Claude session drives the Workstation over SSH
   (the Claude→GitHub→Claude hand-off becomes a fallback, not the default).
2. **Clean split** — Pi = serial-attached prototyping & in-development work;
   Workstation = long-term permanent services.
3. **Future workflow** — a documented, repeatable model for where things run and
   how new services are added.
4. **No data-flow breaks** — every cutover stands up the new path and verifies it
   **before** tearing down the old one.

The concrete first migration is the **EnergyCalibrator test bench backend**
(collector + DB + reports + the new session UI). ZaxEnergySurvey is deferred
(see Decisions).

---

## 2. Machines & roles

| Machine | IP | Role after migration |
|---------|----|--------------------|
| **Pi** | 192.168.110.225 | Serial dev / prototyping; Arduino build+flash; coordinator; **dev MQTT broker** |
| **Workstation** | 192.168.110.11 | Permanent services: bench collector + DB + reports + session UI; **permanent MQTT broker**; InfluxDB + Grafana |
| **Unit D (bench ESP)** | 192.168.110.104 | Unchanged role — reads box serial, polls SDM630, publishes MQTT. Only its `mqtt_host` changes. |

**Owner tags used below:**
`USER` = you, interactive (passwords / physical) · `PI→SSH` = Pi Claude runs it on
the Workstation over SSH · `PI` = Pi Claude runs it on the Pi · `VERIFY` = check
before proceeding.

---

## 3. Pending decisions — confirm before executing

| # | Decision | Recommended default |
|---|----------|---------------------|
| D1 | Broker end-state | Workstation Mosquitto becomes the **single permanent broker**. Migrate **EnergyCalibrator now**; leave **ZAX (Units A/C) on the Pi broker** until later (Unit A is field/user-managed). Keep the Pi broker running until ZAX moves. |
| D2 | Data stack | **Keep SQLite + PDF report** (move as-is — tested/audited) **and additionally feed InfluxDB** so Grafana shows live bench health. No report rewrite. |
| D3 | History | **Copy `cal_data.db`** to the Workstation at cutover so reports keep the full record. |
| D4 | Cutover timing | Perform the Unit D broker switch at a **box-unit session boundary** (between tests) so no single report spans the cutover. |

---

## 4. Data-safety principle (applies to every cutover)

> **Parallel-run, verify, switch, decommission.** Never stop the Pi-side path
> until the Workstation-side path has been observed producing identical data.
> Unit D buffers `sec` in PSRAM and `min`/energy in LittleFS and **replays on
> reconnect**, so a short broker switch loses nothing; `cal_collector` uses
> `INSERT OR REPLACE` so replayed rows are idempotent.

---

## Phase A — Give the Pi session direct control of the Workstation

**A1. Trust the Workstation host key** `[PI]` — _DONE 2026-06-01_
- `ssh-keyscan -t ed25519 192.168.110.11 >> ~/.ssh/known_hosts`

**A2. Authorize the Pi key on the Workstation** `[USER]`
- Run in the Pi prompt: `! ssh-copy-id dan-linux@192.168.110.11` (enter Workstation password once)
- Fallback: SSH in manually and append the Pi pubkey
  (`ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBHlUOM4rW6nJKcHP6uP2YOsN370z076c+ZWkS4EBP1i`)
  to `~/.ssh/authorized_keys`.

**A3. Verify key-based access** `[PI→SSH]` `[VERIFY]`
- `ssh dan-linux@192.168.110.11 'hostname && whoami'` → expect Workstation hostname, `dan-linux`, **no password prompt**.

**A4. Confirm sudo capability** `[PI→SSH]` `[VERIFY]`
- `ssh dan-linux@192.168.110.11 'sudo -n true && echo SUDO_OK'`
- If it prompts/fails: `[USER]` enable passwordless sudo for `dan-linux` (or note that service installs will need interactive sudo).

**A5. Add an SSH alias on the Pi** `[PI]`
- Append to `~/.ssh/config`: `Host ws` / `HostName 192.168.110.11` / `User dan-linux`.
- Verify: `ssh ws hostname`.

**A6. Record the new control model** `[PI→SSH]`
- Update Workstation `COORDINATION.md` + `STATUS.md`: Pi session now has **direct SSH control**; the GitHub task-spec hand-off is the **fallback** when direct control isn't possible. Commit + push.

---

## Phase B — Decide & provision the split (no cutover yet)

**B1. Inventory current Pi services** `[PI]` `[VERIFY]`
- Confirmed running on the Pi today:
  - `mosquitto.service` — broker `:1883` (used by Unit D + ZAX + Workstation parser)
  - `cal_collector.service` → `cal_data.db` _(permanent → move)_
  - `cal_reports.service` — report web `:8080` _(permanent → move)_
  - `zax_directory.service` _(ZAX — keep on Pi for now, see D1)_
  - crons: `daily_report.sh` 00:05; `prune.py` 00:30 (Mon–Sat) + `--vacuum` Sun _(move with reports)_
  - Arduino toolchain / `build_lilygo.sh` _(keep — serial dev)_

**B2. Provision the Workstation** `[PI→SSH]`
- Clone EnergyCalibrator into `/workspace/projects/…/EnergyCalibrator`
- Create a Python venv; install `paho-mqtt`, `reportlab`, `influxdb-client`
- Ensure the ZaxCommon dependency is **not** needed here (collector/report are Python-only; firmware build stays on the Pi)
- Create the DB directory under `/workspace`

**B3. Confirm the Workstation broker** `[PI→SSH]` `[VERIFY]`
- `systemctl status mosquitto` on the Workstation; confirm `:1883` listening
- Decide auth (anonymous vs user/pass) — match what Unit D will use

**B4. Prepare an InfluxDB feed for the bench (D2)** `[PI→SSH]`
- Extend the parser (or add a `cal-parser`) to decode `cal_F07F8C/sec` (76-byte binary)
  and `cal_F07F8C/min` (**JSON**, not 28-byte binary) → InfluxDB `zaxenergy` bucket
- Add `cal_F07F8C` to the units map
- _Defer wiring until Phase C cutover_

---

## Phase C — Cut over EnergyCalibrator (data-safe)

**C1. Parallel-run the Workstation collector** `[PI→SSH]`
- Start `cal_collector.py` on the Workstation **subscribed to the Pi broker (.225)**,
  writing to a Workstation copy of the DB — **while the Pi collector keeps running**.

**C2. Verify the two DBs agree** `[PI]` `[VERIFY]`
- Cross-check a window (row counts + `Σ dkwh` per CT) between Pi `cal_data.db` and
  the Workstation DB — same independent method as the energy audit. Must match.

**C3. Transfer history (D3)** `[PI→SSH]`
- Snapshot the Pi `cal_data.db` (WAL checkpoint) and copy it to the Workstation;
  reconcile with the parallel-run rows (idempotent `INSERT OR REPLACE`).

**C4. Switch the broker (D4 — at a session boundary)** `[USER]` + `[PI]`
- Re-point Unit D: `POST /api/config` with `mqtt_host=192.168.110.11`
  (or via the web UI Config tab). Unit D reconnects and **replays its buffer**.
- Point the Workstation collector at the **local** broker (`127.0.0.1`).
- Stop + disable the **Pi** `cal_collector.service`.
- `VERIFY`: Workstation DB receiving fresh `sec`/`min`; `/api/sysinfo` shows MQTT connected.

**C5. Move reporting** `[PI→SSH]`
- Install `cal_collector` + report web as systemd services on the Workstation
- Recreate the daily-report + prune crons on the Workstation; **remove them from the Pi**
- Bring up the report web server (decide URL: `http://192.168.110.11:8080/`)

**C6. Wire the InfluxDB feed** `[PI→SSH]`
- Enable the `cal` parser path → InfluxDB; add/extend a Grafana bench dashboard

**C7. End-to-end verification** `[PI]` `[VERIFY]`
- Generate a report on the Workstation for a known window → matches the Pi's last report
- Data fresh (`<2 s` collector lag); Grafana bench panel populating
- Run `report/tests/` + `arduino/tests/test_energy_accumulator.py` on the Workstation

**C8. Decommission Pi bench services** `[PI]`
- `disable --now` `cal_collector.service`, `cal_reports.service`
- Remove the bench crons (already done in C5); archive the Pi `cal_data.db`
- Leave the Pi broker running (ZAX still uses it)

---

## Phase D — Future workflow & documentation

**D1. Single source-of-truth infra doc** `[PI→SSH]`
- One doc (this repo) describing: **what runs where**, the **data-flow/broker map**,
  and **deploy steps** per service. Link it from `README.md`.

**D2. Operating rules** `[PI→SSH]`
- New **permanent** service → on the Workstation, via direct SSH from the Pi session
- New **prototype / serial** work → on the Pi
- Firmware build/flash stays on the Pi (USB serial)

**D3. Health checks** `[PI→SSH]`
- A quick status script per machine (services up, broker connected, collector lag,
  disk free) for start-of-session checks.

---

## Phase E — (Follow-on) Build the bench session UI

The original objective. Specced separately once the backend lives on the
Workstation. Summary of the target: web app to **enter a box-unit serial → start a
test session → stop → generate/download the session report**. Adds a `sessions`
table (serial, start_ts, stop_ts, status); the report generator gains a
session-window scope (`--from/--to`) alongside `--date`. Live monitoring via
Grafana during a session.

---

## 5. Rollback summary

| Phase | If it goes wrong |
|-------|------------------|
| A | No effect on data; just don't use SSH control |
| C1–C3 | Parallel-run only — Pi path untouched; stop the Workstation collector |
| C4 | Re-point Unit D `mqtt_host` back to `.225`, restart the Pi `cal_collector`; buffer replays cover the gap |
| C5–C8 | Re-enable the Pi services/crons; Pi DB retained until Workstation proven |

The Pi path remains the rollback target until Phase C is fully verified.

---

## 6. Appendix — current-state snapshot (2026-06-01)

**Pi (192.168.110.225):** `mosquitto` (:1883), `cal_collector` → `cal_data.db`,
`cal_reports` (:8080), `zax_directory`; crons (daily report 00:05, prune 00:30);
Arduino toolchain. Unit D `mqtt_host=192.168.110.225`, topic `cal_F07F8C`.

**Workstation (192.168.110.11, Ubuntu 26.04, /workspace 208 GB free):**
`mosquitto` (:1883, idle for bench), InfluxDB 2.7.11 (org `zax`, bucket
`zaxenergy`), Grafana 13.0.1 (:3000), `zax-parser.service` (subscribes Pi `.225`,
Units A+C), Flutter/Android.

**Bench MQTT formats:** `cal_F07F8C/sec` = 76-byte binary SecRecord;
`cal_F07F8C/min` = **JSON** (box + meter + deviation) — differs from ZAX's
28-byte binary `min`, so the parser needs bench-specific handling.

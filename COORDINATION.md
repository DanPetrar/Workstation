# Workstation — Coordination Guide

_Read this at the start of every Claude Code session on this machine._

---

## Two-machine setup

| Machine | Role | Claude Code |
|---------|------|-------------|
| **Pi** (192.168.20.225) | Coordinator — writes task specs, reviews results, maintains project docs | Yes |
| **Workstation** (this machine) | Executor — implements tasks, builds, tests, commits results | Yes |

**The user works on both machines.** Pi Claude and Workstation Claude are separate instances with no shared memory. The Pi Claude knows the ZaxEnergy project in full detail; task specs written by Pi Claude are self-contained so Workstation Claude can execute them without prior context.

### Control model (since 2026-06-02 — migration Phase A)

The Pi session now has **direct SSH control** of this Workstation
(`ssh ws` → `dan-linux@192.168.20.11`, key-based, passwordless sudo). This is the
**default** path: the Pi Claude runs commands here directly over SSH.

The **GitHub task-spec hand-off below is the fallback** — used for work that must run
locally on the Workstation (a Claude session here, interactive tools), or when direct
SSH is unavailable.

> **Where things run** (permanent svc → Workstation; prototype/serial + firmware →
> Pi) and the full service/data-flow map are in [`INFRASTRUCTURE.md`](INFRASTRUCTURE.md)
> — the source of truth. Run `infrastructure/health-{pi,ws}.sh` at session start.

---

## How tasks work

1. Pi Claude writes a task spec in this repo or in a project repo, commits, pushes
2. User pulls on Workstation, opens Claude Code, says "implement tasks/TASK-XXX.md" (or similar)
3. Workstation Claude reads the spec, implements, commits results, pushes
4. Pi Claude reviews the diff on next session, updates the task index, writes the next task

**Task specs are self-contained.** They include: goal, full context (API formats, payload structures, config), exact files to create or edit, and acceptance criteria. Do not assume prior knowledge of ZaxEnergy.

---

## Task index

All tasks tracked in [`tasks/INDEX.md`](tasks/INDEX.md).

| Prefix | Direction |
|--------|-----------|
| `W-` | Workstation machine management (setup, inventory) |
| `I-` | Infrastructure stack (MQTT, InfluxDB, parser, Grafana) |
| Android tasks | Live in `ZaxEnergySurvey/android/tasks/` — same workflow |

---

## Active directions

### 1 — Infrastructure stack
Install and configure a data pipeline on this machine:
- **MQTT subscriber** — connect to the Workstation's own Mosquitto broker (`localhost:1883`), subscribe to `zax_E47730/#`, `zax_E482C0/#`, `zax_73DA28/#`, `zax_F07F8C/#` (Units A/B/C/D)
- **Parser** — decode binary ZaxEnergy payloads (`zax/sec` = 76 bytes, `zax/min` = 28 bytes) into structured data
- **InfluxDB 2.x** — time series database storing decoded readings
- **Grafana** — visualization dashboards for energy and power data

> MQTT broker is on this Workstation — units publish here directly (no Pi relay, since 2026-06-24). See [`INFRASTRUCTURE.md`](INFRASTRUCTURE.md) for the full data-flow map.

### 2 — Android app (ZaxEnergy companion)
Flutter app for live dashboard and configuration of ZaxEnergy units over WiFi REST.
Task specs: `ZaxEnergySurvey/android/tasks/`

---

## ZaxEnergy context (brief)

ESP32-based 3-phase energy monitors. Each unit:
- Publishes binary MQTT to Pi broker every second (`<prefix>/sec`, 76 bytes) and every minute (`<prefix>/min`, 28 bytes)
- Exposes REST API at its local IP (e.g. `http://192.168.20.231`)

**MQTT binary formats:**

`<prefix>/sec` — 76 bytes, little-endian:
```
uint32  ts       Unix timestamp
float×3 v        Voltage V        — R, S, T
float×3 a        Current A        — R, S, T
float×3 w        Active power W   — R, S, T
float×3 hz       Frequency Hz     — R, S, T
int32×3 var      Reactive VAr     — R, S, T
float×3 pf       Power factor     — R, S, T
```
Python unpack: `struct.unpack('<I 3f 3f 3f 3f 3i 3f', payload)`

`<prefix>/min` — 28 bytes, little-endian:
```
uint32  ts       Unix timestamp
float×3 kwh      Active energy kWh   — R, S, T
float×3 kvarh    Reactive energy kVArh — R, S, T
```
Python unpack: `struct.unpack('<I 3f 3f', payload[:28])`

**Known units:**

| Name | IP | MQTT prefix |
|------|----|-------------|
| Unit_A | 192.168.20.231 | zax_E47730 |
| Unit_B | 192.168.20.232 | zax_E482C0 |
| Unit_C | 192.168.20.233 | zax_73DA28 |
| Unit_D | 192.168.20.234 | zax_F07F8C |

---

## Reporting results

After completing a task:
1. Update `tasks/INDEX.md` — mark task as Done, add a one-line result note
2. Update `inventory.md` if any tools were installed or changed
3. Commit with message referencing the task ID (e.g. `W-001: inventory current tools`)
4. Push — Pi Claude will review on next session

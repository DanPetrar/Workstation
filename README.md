# Workstation

Development machine for Android and other project-specific work coordinated from the ZaxEnergy Pi.

---

## Hardware

| Item | Detail |
|------|--------|
| CPU | Intel Core i3 |
| RAM | 8 GB |
| Storage | 2 × 240 GB SSD |
| OS | Debian Linux |

## Purpose

Dedicated workstation for tasks that require a full desktop development environment — primarily Android/Flutter development. Machine state is tracked here; project task specs live in their respective project repos.

## Coordination model

- **Pi** (192.168.110.225) — coordination hub; runs Claude Code; writes task specs to project repos; reviews results
- **Workstation** (this machine) — executes task specs; implements, builds, and tests; commits results back

Task specs for the Android app: `ZaxEnergySurvey/android/tasks/`

## Infrastructure (source of truth)

See [`INFRASTRUCTURE.md`](INFRASTRUCTURE.md) — what runs where, the data-flow/broker map, operating rules, and per-service deploy steps. Per-machine health checks live in [`infrastructure/`](infrastructure/) (`health-pi.sh`, `health-ws.sh`).

## Installed tools

See [`inventory.md`](inventory.md) — maintained by Claude Code; updated whenever tools are installed, removed, or reconfigured.

## Setup history

See [`setup/`](setup/) — one file per setup session, timestamped.

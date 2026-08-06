# Workstation — Inventory

_Last updated: 2026-08-06_

Maintained by Claude Code. Updated whenever a tool is installed, removed, or reconfigured.

---

## System

| Item | Value |
|------|-------|
| OS | Ubuntu 26.04 LTS (Resolute) |
| Kernel | 7.0.0-28-generic |
| Architecture | x86_64 |
| RAM | 7.1 GiB total, ~5.7 GiB available |
| OS disk (`/dev/nvme0n1p2`) | 233 GB — 49 GB used, 173 GB free |
| Workspace disk (`/dev/sda` → `/workspace`) | 220 GB — 1.3 GB used, 207 GB free |
| IP address | 192.168.20.11 |

---

## Core tools

| Tool | Version | Status |
|------|---------|--------|
| Git | 2.53.0 | ✅ installed |
| curl | 8.18.0 | ✅ installed |
| wget | 1.25.0 | ✅ installed |
| Python 3 | 3.14.4 | ✅ installed |
| pip 3 | 25.1.1 | ✅ installed |
| Node.js | 20.20.2 | ✅ installed |
| npm | 10.8.2 | ✅ installed |
| Java | OpenJDK 17.0.19 | ✅ installed |

---

## Claude Code

| Tool | Version | Status |
|------|---------|--------|
| Claude Code | — | ➖ not installed (verified 2026-08-06: no `claude` binary on this machine) — Workstation is driven via direct SSH from the Pi/coordinator session (see `COORDINATION.md`); a local session here is the fallback path and is not currently set up |

---

## Flutter / Android

| Tool | Version | Status |
|------|---------|--------|
| Flutter SDK | 3.44.0 (stable) | ✅ installed — `/opt/flutter` |
| Android Studio | not installed | ➖ not needed (CLI tools only) |
| Android SDK / adb | platform-tools 37.0.0, API 36 | ✅ installed — `~/Android/Sdk` |

---

## Data stack

| Tool | Version | Service status |
|------|---------|----------------|
| InfluxDB | v2.7.11 (server) / dev CLI | ✅ active — org `zax`, bucket `zaxenergy` |
| Grafana | 13.0.1+security-01 | ✅ active — InfluxDB data source + Power & Energy dashboards |
| Mosquitto (MQTT) | 2.0.22 | ✅ active |
| zax-parser | — | ✅ active — MQTT→InfluxDB, Unit_A/B/C/D, subscribes localhost broker |
| Android emulator | API 36, google_apis x86_64 | ✅ AVD `zax_test` — start with `~/start-zax-emulator.sh` |

---

## Network

| Check | Result |
|-------|--------|
| Workstation IP | 192.168.20.11 |
| Pi (192.168.20.225) | ✅ reachable (0.125 ms) |

---

_Update this file after every install/remove/reconfigure action._

# Workstation — Inventory

_Last updated: 2026-05-27_

Maintained by Claude Code. Updated whenever a tool is installed, removed, or reconfigured.

---

## System

| Item | Value |
|------|-------|
| OS | Ubuntu 26.04 LTS (Resolute) |
| Kernel | 7.0.0-15-generic |
| Architecture | x86_64 |
| RAM | 7.1 GiB total, ~5.4 GiB available |
| OS disk (`/dev/nvme0n1p2`) | 233 GB — 27 GB used, 195 GB free |
| Workspace disk (`/dev/sda` → `/workspace`) | 220 GB — 39 MB used, 208 GB free |
| IP address | 192.168.110.11 |

---

## Core tools

| Tool | Version | Status |
|------|---------|--------|
| Git | 2.53.0 | ✅ installed |
| curl | 8.18.0 | ✅ installed |
| wget | 1.25.0 | ✅ installed |
| Python 3 | 3.14.4 | ✅ installed |
| pip 3 | 26.1.1 | ✅ installed |
| Node.js | 20.20.2 | ✅ installed |
| npm | 10.8.2 | ✅ installed |
| Java | OpenJDK 17.0.18 | ✅ installed |

---

## Claude Code

| Tool | Version | Status |
|------|---------|--------|
| Claude Code | 2.1.152 | ✅ installed |

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
| zax-parser | — | ✅ active — MQTT→InfluxDB, Unit_A + Unit_C |

---

## Network

| Check | Result |
|-------|--------|
| Workstation IP | 192.168.110.11 |
| Pi (192.168.110.225) | ✅ reachable (0.285 ms) |

---

_Update this file after every install/remove/reconfigure action._

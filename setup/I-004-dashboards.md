# I-004 — Grafana dashboards provisioned

_Completed: 2026-05-27_

---

## Grafana folder

| Item | Value |
|------|-------|
| Folder name | ZaxEnergy |
| Folder UID | `ffnbi3smi4ruod` |

---

## Dashboards

| Dashboard | UID | URL | Status |
|-----------|-----|-----|--------|
| ZaxEnergy — Power | `zax-power` | http://192.168.110.11:3000/d/zax-power | ✅ created |
| ZaxEnergy — Energy | `zax-energy` | http://192.168.110.11:3000/d/zax-energy | ✅ created |

---

## Power dashboard panels

6 time-series panels. Unit dropdown (Unit_A / Unit_C) filters all panels.

| Panel | Field | Notes |
|-------|-------|-------|
| Voltage (V) | `v` | 3 series (R, S, T) per unit — ~239–240 V live |
| Current (A) | `a` | 3 series |
| Active Power (W) | `w` | 3 series |
| Frequency (Hz) | `hz` | 3 series — ~50 Hz live |
| Power Factor | `pf` | 3 series |
| Reactive Power (VAr) | `var` | 3 series |

Refresh: 5 s. Default time range: last 15 minutes.

---

## Energy dashboard panels

2 time-series panels showing all units and phases.

| Panel | Field |
|-------|-------|
| Active Energy (kWh) | `kwh` |
| Reactive Energy (kVArh) | `kvarh` |

Refresh: 1 min. Default time range: last 24 hours.

---

## Admin password change

Grafana admin password changed from default `admin` to `zaxenergy2026` (Step 0 of this task).

---

## Screenshots

Automated screenshots were not taken — the machine has no display and the `grafana-image-renderer` plugin is not installed. Dashboards can be viewed in a browser at the URLs above from any machine on the 192.168.110.x network.

To install the render plugin later: `grafana-cli plugins install grafana-image-renderer`

---

## Issues

None. Both dashboards created successfully via API on first attempt.

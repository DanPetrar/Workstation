# TASK I-004 — Build Grafana dashboards (power + energy)

**Assigned by:** Pi Claude  
**Direction:** Infrastructure stack  
**Depends on:** I-002 ✅, I-003 ✅  
**Status:** Ready

---

## Goal

Create two Grafana dashboards using the InfluxDB data already flowing from the parser:
1. **ZaxEnergy — Power** — real-time per-phase electrical measurements
2. **ZaxEnergy — Energy** — cumulative energy totals per unit/phase

Provision them via the Grafana API (repeatable, no manual clicks).

---

## Context

| Item | Value |
|------|-------|
| Grafana URL | http://localhost:3000 |
| Grafana admin | `admin` / `admin` (change password — see Step 0) |
| Data source name | `ZaxEnergy-InfluxDB` |
| Data source UID | `ffnbf64waxe68a` |
| InfluxDB org | `zax` |
| InfluxDB bucket | `zaxenergy` |
| Measurement: power | tags: `unit` (Unit_A, Unit_C), `phase` (R, S, T); fields: `v`, `a`, `w`, `hz`, `var`, `pf` |
| Measurement: energy | tags: `unit`, `phase`; fields: `kwh`, `kvarh` |

---

## Step 0 — Change Grafana admin password

```bash
curl -s -X PUT http://admin:admin@localhost:3000/api/user/password \
  -H "Content-Type: application/json" \
  -d '{"oldPassword":"admin","newPassword":"<NEW_PASS>","confirmNew":"<NEW_PASS>"}'
```

Record the new password in `setup/I-002-grafana.md` (update the admin password row).

---

## Step 1 — Create dashboard folder

```bash
GPASS=<NEW_PASS>

curl -s -X POST http://admin:${GPASS}@localhost:3000/api/folders \
  -H "Content-Type: application/json" \
  -d '{"title":"ZaxEnergy"}'
```

Note the returned `uid` — use it as `folderUid` in Step 2 and Step 3.

---

## Step 2 — Power dashboard

One dashboard with a **unit variable** (dropdown: Unit_A, Unit_C) and six time-series panels — one per field. Each panel shows all three phases (R, S, T) as separate series.

### Dashboard JSON template

Save as `/tmp/power-dashboard.json` (replace `<FOLDER_UID>` and `<DATASOURCE_UID>`):

```json
{
  "folderUid": "<FOLDER_UID>",
  "dashboard": {
    "title": "ZaxEnergy — Power",
    "uid": "zax-power",
    "timezone": "browser",
    "refresh": "5s",
    "time": {"from": "now-15m", "to": "now"},
    "templating": {
      "list": [{
        "name": "unit",
        "type": "custom",
        "label": "Unit",
        "current": {"value": "Unit_A", "text": "Unit_A"},
        "options": [
          {"value": "Unit_A", "text": "Unit_A"},
          {"value": "Unit_C", "text": "Unit_C"}
        ]
      }]
    },
    "panels": [
      {
        "type": "timeseries", "title": "Voltage (V)", "gridPos": {"x":0,"y":0,"w":12,"h":8},
        "datasource": {"type":"influxdb","uid":"<DATASOURCE_UID>"},
        "targets": [{"refId":"R","query":"from(bucket:\"zaxenergy\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn:(r) => r._measurement == \"power\" and r.unit == \"${unit}\" and r._field == \"v\")"},
                    {"refId":"S","query":"from(bucket:\"zaxenergy\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn:(r) => r._measurement == \"power\" and r.unit == \"${unit}\" and r._field == \"v\" and r.phase == \"S\")"},
                    {"refId":"T","query":"from(bucket:\"zaxenergy\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn:(r) => r._measurement == \"power\" and r.unit == \"${unit}\" and r._field == \"v\" and r.phase == \"T\")"}]
      },
      {
        "type": "timeseries", "title": "Current (A)", "gridPos": {"x":12,"y":0,"w":12,"h":8},
        "datasource": {"type":"influxdb","uid":"<DATASOURCE_UID>"},
        "targets": [{"refId":"A","query":"from(bucket:\"zaxenergy\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn:(r) => r._measurement == \"power\" and r.unit == \"${unit}\" and r._field == \"a\")"}]
      },
      {
        "type": "timeseries", "title": "Active Power (W)", "gridPos": {"x":0,"y":8,"w":12,"h":8},
        "datasource": {"type":"influxdb","uid":"<DATASOURCE_UID>"},
        "targets": [{"refId":"A","query":"from(bucket:\"zaxenergy\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn:(r) => r._measurement == \"power\" and r.unit == \"${unit}\" and r._field == \"w\")"}]
      },
      {
        "type": "timeseries", "title": "Frequency (Hz)", "gridPos": {"x":12,"y":8,"w":12,"h":8},
        "datasource": {"type":"influxdb","uid":"<DATASOURCE_UID>"},
        "targets": [{"refId":"A","query":"from(bucket:\"zaxenergy\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn:(r) => r._measurement == \"power\" and r.unit == \"${unit}\" and r._field == \"hz\")"}]
      },
      {
        "type": "timeseries", "title": "Power Factor", "gridPos": {"x":0,"y":16,"w":12,"h":8},
        "datasource": {"type":"influxdb","uid":"<DATASOURCE_UID>"},
        "targets": [{"refId":"A","query":"from(bucket:\"zaxenergy\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn:(r) => r._measurement == \"power\" and r.unit == \"${unit}\" and r._field == \"pf\")"}]
      },
      {
        "type": "timeseries", "title": "Reactive Power (VAr)", "gridPos": {"x":12,"y":16,"w":12,"h":8},
        "datasource": {"type":"influxdb","uid":"<DATASOURCE_UID>"},
        "targets": [{"refId":"A","query":"from(bucket:\"zaxenergy\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn:(r) => r._measurement == \"power\" and r.unit == \"${unit}\" and r._field == \"var\")"}]
      }
    ],
    "schemaVersion": 38,
    "version": 1
  },
  "overwrite": true
}
```

### Import

```bash
curl -s -X POST http://admin:${GPASS}@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @/tmp/power-dashboard.json
```

Expected: `{"status":"success","uid":"zax-power","url":"/d/zax-power/..."}`.

---

## Step 3 — Energy dashboard

Two panels: cumulative kWh and kVArh per phase, for both units side by side.

Save as `/tmp/energy-dashboard.json`:

```json
{
  "folderUid": "<FOLDER_UID>",
  "dashboard": {
    "title": "ZaxEnergy — Energy",
    "uid": "zax-energy",
    "timezone": "browser",
    "refresh": "1m",
    "time": {"from": "now-24h", "to": "now"},
    "panels": [
      {
        "type": "timeseries", "title": "Active Energy (kWh)", "gridPos": {"x":0,"y":0,"w":24,"h":10},
        "datasource": {"type":"influxdb","uid":"<DATASOURCE_UID>"},
        "targets": [{"refId":"A","query":"from(bucket:\"zaxenergy\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn:(r) => r._measurement == \"energy\" and r._field == \"kwh\")"}]
      },
      {
        "type": "timeseries", "title": "Reactive Energy (kVArh)", "gridPos": {"x":0,"y":10,"w":24,"h":10},
        "datasource": {"type":"influxdb","uid":"<DATASOURCE_UID>"},
        "targets": [{"refId":"A","query":"from(bucket:\"zaxenergy\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn:(r) => r._measurement == \"energy\" and r._field == \"kvarh\")"}]
      }
    ],
    "schemaVersion": 38,
    "version": 1
  },
  "overwrite": true
}
```

```bash
curl -s -X POST http://admin:${GPASS}@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @/tmp/energy-dashboard.json
```

---

## Step 4 — Verify

Open in browser and confirm panels show data:

```
http://192.168.110.11:3000/d/zax-power
http://192.168.110.11:3000/d/zax-energy
```

Take a screenshot of each dashboard with data visible and save to:
- `setup/screenshots/I-004-power.png`
- `setup/screenshots/I-004-energy.png`

---

## Deliverables

1. **Save dashboard JSONs** (with real UIDs substituted) to:
   - `infrastructure/grafana-power-dashboard.json`
   - `infrastructure/grafana-energy-dashboard.json`
2. **Update `setup/I-002-grafana.md`** — add new admin password and dashboard URLs
3. **Create `setup/I-004-dashboards.md`** — dashboard UIDs, folder UID, screenshot paths, any issues
4. **Save screenshots** to `setup/screenshots/`
5. **Update `inventory.md`** — add Grafana dashboards row to data stack
6. **Update `tasks/INDEX.md`** and `STATUS.md` — mark I-004 Done, set status to `Done — awaiting Pi review`
7. **Commit and push** — message: `I-004: Grafana power + energy dashboards provisioned`

---

## Acceptance criteria

- Both dashboards visible at http://192.168.110.11:3000
- Power dashboard shows live time-series data for Unit_A and Unit_C, switchable via unit variable
- Energy dashboard shows kWh and kVArh trends
- Screenshots in repo confirm data is visible
- Admin password no longer default `admin`

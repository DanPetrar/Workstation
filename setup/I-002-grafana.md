# I-002 — Grafana: InfluxDB Data Source Setup

_Completed: 2026-05-27_

## Grafana details

| Item | Value |
|------|-------|
| Version | 13.0.1+security-01 |
| URL | http://localhost:3000 |
| Admin password | `zaxenergy2026` (changed in I-004) |
| Service | systemd `grafana-server`, active |

## Data source added

| Field | Value |
|-------|-------|
| Name | ZaxEnergy-InfluxDB |
| Type | InfluxDB (Flux query language) |
| ID | 1 |
| UID | `ffnbf64waxe68a` |
| URL | http://localhost:8086 |
| Organisation | zax |
| Default bucket | zaxenergy |
| Token | see `setup/I-001-influxdb.md` (token from I-001) |

## Health check result

```
GET /api/datasources/uid/ffnbf64waxe68a/health
→ {"message":"datasource is working. 1 buckets found","status":"OK"}
```

Connection verified — Grafana can reach InfluxDB and sees the `zaxenergy` bucket.

## Dashboards (added in I-004)

| Dashboard | UID | URL |
|-----------|-----|-----|
| ZaxEnergy — Power | `zax-power` | http://192.168.110.11:3000/d/zax-power |
| ZaxEnergy — Energy | `zax-energy` | http://192.168.110.11:3000/d/zax-energy |
| Folder | `ffnbi3smi4ruod` | ZaxEnergy |

## Notes

- Grafana 13 uses UID-based health endpoint (`/api/datasources/uid/<uid>/health`), not the older ID-based one.
- Data source was set as the default data source for the organisation.
- No issues encountered.

# TASK I-002 — Verify and configure Grafana → InfluxDB connection

**Assigned by:** Pi Claude  
**Direction:** Infrastructure stack  
**Depends on:** I-001 ✅ (need org, bucket, token from I-001)  
**Status:** Waiting on I-001

---

## Goal

Confirm Grafana is running and accessible, then add InfluxDB as a data source so dashboards can be built in I-004.

---

## Step 1 — Verify Grafana is accessible

```bash
systemctl status grafana-server
curl -s http://localhost:3000/api/health
```

Expected: service active, health endpoint returns `{"database":"ok","version":"..."}`.

Open in browser: `http://192.168.110.11:3000`  
Default credentials if not changed: `admin` / `admin` (Grafana will prompt to change on first login).

---

## Step 2 — Add InfluxDB data source via API

Use the Grafana HTTP API to add the data source (avoids manual UI steps, repeatable):

```bash
# Replace <GRAFANA_PASS> with actual admin password
# Replace <INFLUX_TOKEN> with token from I-001

curl -s -X POST http://admin:<GRAFANA_PASS>@localhost:3000/api/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ZaxEnergy-InfluxDB",
    "type": "influxdb",
    "url": "http://localhost:8086",
    "access": "proxy",
    "jsonData": {
      "version": "Flux",
      "organization": "zaxenergy",
      "defaultBucket": "zaxenergy"
    },
    "secureJsonData": {
      "token": "<INFLUX_TOKEN>"
    }
  }'
```

Expected response: `{"datasource":{...},"id":1,"message":"Datasource added","name":"ZaxEnergy-InfluxDB"}`

If the data source already exists, the call will fail with 409 — that's fine, just verify it in the UI.

---

## Step 3 — Verify the connection

```bash
# Get the datasource ID (should be 1 or check the list)
curl -s http://admin:<GRAFANA_PASS>@localhost:3000/api/datasources | python3 -m json.tool

# Test the data source connection
curl -s http://admin:<GRAFANA_PASS>@localhost:3000/api/datasources/1/health
```

Expected: `{"message":"OK","status":"OK"}`

---

## Deliverables

1. **Create `setup/I-002-grafana.md`** with:
   - Grafana version
   - Admin password (if changed from default)
   - Data source name and ID
   - Any issues encountered

2. **Update `inventory.md`** — replace the Grafana row with confirmed version and note "InfluxDB data source configured".

3. **Update `tasks/INDEX.md`** — mark I-002 Done.

4. **Commit and push** — message: `I-002: verify Grafana, add InfluxDB data source`

---

## Acceptance criteria

- Grafana accessible at http://192.168.110.11:3000
- Data source `ZaxEnergy-InfluxDB` added and health check passes
- Details saved in `setup/I-002-grafana.md`

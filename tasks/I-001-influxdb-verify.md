# TASK I-001 — Verify and configure InfluxDB for ZaxEnergy

**Assigned by:** Pi Claude  
**Direction:** Infrastructure stack  
**Depends on:** W-001 ✅  
**Status:** Pending

---

## Goal

Confirm InfluxDB 2.x is correctly installed, running, and accessible. Create the org, bucket, and API token that the ZaxEnergy parser (I-003) and Grafana (I-002) will use.

---

## Step 1 — Verify server version and status

```bash
# Check server is running
systemctl status influxdb

# Get server version (different from CLI version)
curl -s http://localhost:8086/health
curl -s http://localhost:8086/api/v2/version 2>/dev/null || \
  influx ping --host http://localhost:8086

# Check CLI version in detail
influx version
```

Expected: server responding on port 8086, version 2.x.x.  
If the server returns a 404 or the version shows 3.x, note it — the API and token model differ and Pi Claude will rewrite I-003 accordingly.

---

## Step 2 — Check existing setup

```bash
# List existing orgs
influx org list

# List existing buckets
influx bucket list

# List existing tokens (if any)
influx auth list
```

Note what already exists. If an org, bucket, and token for ZaxEnergy are already set up, skip Step 3 and use those values.

---

## Step 3 — Create ZaxEnergy org, bucket, and token (if not already present)

```bash
# Create org (skip if already exists)
influx org create --name zaxenergy

# Create bucket with 30-day retention (skip if already exists)
influx bucket create \
  --name zaxenergy \
  --org zaxenergy \
  --retention 30d

# Create API token with read+write access to the bucket
influx auth create \
  --org zaxenergy \
  --read-buckets \
  --write-buckets \
  --description "ZaxEnergy parser + Grafana"
```

**Save the token** — you will need it for I-002 (Grafana) and I-003 (parser). The token is shown only once on creation.

---

## Step 4 — Verify write access

```bash
# Write a test point
influx write \
  --org zaxenergy \
  --bucket zaxenergy \
  --token <YOUR_TOKEN> \
  "test,unit=test value=1.0"

# Read it back
influx query \
  --org zaxenergy \
  --token <YOUR_TOKEN> \
  'from(bucket:"zaxenergy") |> range(start: -5m) |> filter(fn: (r) => r._measurement == "test")'
```

Expected: the test point appears in the query result.

```bash
# Clean up test point
influx delete \
  --org zaxenergy \
  --bucket zaxenergy \
  --token <YOUR_TOKEN> \
  --start 1970-01-01T00:00:00Z \
  --stop $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --predicate '_measurement="test"'
```

---

## Deliverables

1. **Create `setup/I-001-influxdb.md`** with:
   - InfluxDB server version (from `/health` or `/api/v2/version`)
   - Org name
   - Bucket name
   - API token (full token string — this file is private to this repo)
   - Any issues encountered

2. **Update `inventory.md`** — replace the InfluxDB row with the real server version.

3. **Update `tasks/INDEX.md`** — mark I-001 Done with a one-line result.

4. **Commit and push** — message: `I-001: verify InfluxDB, create zaxenergy org/bucket/token`

---

## Acceptance criteria

- InfluxDB server version confirmed and recorded
- Org `zaxenergy`, bucket `zaxenergy` exist
- API token created and saved in `setup/I-001-influxdb.md`
- Test write + read cycle passes

# SESSION CLOSE — Verify and tidy before next session

**Assigned by:** Pi Claude  
**Type:** Housekeeping  
**Status:** Ready

---

## Goal

Verify all services are healthy and all repos are clean so the next session can start without surprises.

---

## Step 1 — Verify infrastructure services

```bash
systemctl is-active influxdb grafana-server zax-parser
```

Expected: three lines of `active`. If any shows `failed` or `inactive`, check with `journalctl -u <service> -n 30` and restart if needed: `sudo systemctl restart <service>`.

Quick data check — confirm parser is still writing:

```bash
TOKEN=$(grep "Token |" ~/Workstation/setup/I-001-influxdb.md | awk '{print $NF}')
influx query --org zax --token $TOKEN \
  'from(bucket:"zaxenergy") |> range(start: -5m) |> filter(fn:(r) => r._measurement == "power") |> count() |> limit(n:1)'
```

Expected: non-zero count (data arriving from Unit A or Unit C).

---

## Step 2 — Verify git repos are clean

```bash
# Workstation repo
git -C ~/Workstation status

# ZaxEnergySurvey repo
git -C ~/ZaxEnergySurvey status
```

Expected: both show `nothing to commit, working tree clean`. If there are uncommitted changes, commit them with a descriptive message.

---

## Step 3 — Update STATUS.md

Update the `## Active tasks` section to reflect no active tasks and add a session close note:

```markdown
## Active tasks

_Session closed 2026-05-27. All infrastructure + Android demo tasks complete._
_Start next session by reading this file and ZaxEnergySurvey/android/ZaxMonitor_Demo.md._
```

---

## Step 4 — Confirm Grafana is reachable

```bash
curl -s http://localhost:3000/api/health | python3 -m json.tool
```

Expected: `{"database":"ok","version":"13.0.1+security-01",...}`.

Also confirm it is reachable from the network (from another machine or just verify the bind address):

```bash
ss -tlnp | grep 3000
```

Expected: Grafana listening on `0.0.0.0:3000` (not just 127.0.0.1).

---

## Deliverables

1. **Update `STATUS.md`** with session close note and service health result
2. **Commit and push** — message: `Session close 2026-05-27: services verified, repos clean`

---

## What to expect next session

- Pi will read `STATUS.md` and this INDEX to pick up context
- Likely next directions: extend Android app (more screens / features), Grafana dashboard refinements, or new firmware iteration
- If any service is found degraded: report it in STATUS.md and Pi will write a fix task

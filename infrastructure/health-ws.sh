#!/usr/bin/env bash
# health-ws.sh — start-of-session health check for the Workstation (192.168.110.11).
# Run locally on the WS:  bash infrastructure/health-ws.sh
# (or from the Pi:  ssh ws 'bash ~/Workstation/infrastructure/health-ws.sh')
# See INFRASTRUCTURE.md section 1 for what should be running here.
set -u

VENV_PY=/workspace/projects/EnergyCalibrator/.venv/bin/python3
CAL_DB=/workspace/cal-data/cal_data.db
LAG_WARN=5      # seconds
LAG_FAIL=60     # seconds

fails=0
ok()   { printf 'PASS  %s\n' "$1"; }
warn() { printf 'WARN  %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; fails=$((fails+1)); }

echo "== Workstation health ($(hostname), $(date '+%Y-%m-%d %H:%M')) =="

# Core permanent services (dormant zax-bridge/zax-influx intentionally excluded)
for svc in mosquitto influxdb grafana-server zax-parser cal_collector cal_reports cal-parser; do
  if systemctl is-active --quiet "$svc"; then ok "$svc active"; else bad "$svc NOT active"; fi
done

# Broker port
if ss -tln 2>/dev/null | grep -q ':1883 '; then ok "broker listening :1883"; else bad "broker :1883 not listening"; fi

# Bench collector lag (newest cal_sec row vs now) — via venv python (no sqlite3 CLI here)
if [ -x "$VENV_PY" ] && [ -f "$CAL_DB" ]; then
  lag=$("$VENV_PY" - "$CAL_DB" <<'PY' 2>/dev/null
import sqlite3, sys, time
c = sqlite3.connect(sys.argv[1])
row = c.execute("SELECT MAX(ts) FROM cal_sec").fetchone()
print(int(time.time()) - row[0] if row and row[0] is not None else -1)
PY
)
  if   [ -z "$lag" ];            then bad "collector lag: query failed"
  elif [ "$lag" -lt 0 ];        then warn "collector lag: cal_sec empty (no rows yet)"
  elif [ "$lag" -ge $LAG_FAIL ]; then bad "collector lag ${lag}s (>= ${LAG_FAIL}s — stalled?)"
  elif [ "$lag" -ge $LAG_WARN ]; then warn "collector lag ${lag}s"
  else ok "collector lag ${lag}s"; fi
else
  bad "collector lag: venv python or cal_data.db missing"
fi

# Disk free on / and /workspace
for mnt in / /workspace; do
  read -r used_pct avail < <(df -h "$mnt" | awk 'NR==2{gsub("%","",$5); print $5, $4}')
  if   [ "${used_pct:-100}" -ge 90 ]; then bad "disk $mnt ${used_pct}% used (${avail} free)"
  elif [ "${used_pct:-100}" -ge 80 ]; then warn "disk $mnt ${used_pct}% used (${avail} free)"
  else ok "disk $mnt ${used_pct}% used (${avail} free)"; fi
done

echo "== $( [ $fails -eq 0 ] && echo 'all checks passed' || echo "$fails check(s) FAILED" ) =="
exit "$fails"

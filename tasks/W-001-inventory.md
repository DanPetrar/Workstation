# TASK W-001 — Inventory current tools and environment

**Assigned by:** Pi Claude  
**Direction:** Workstation setup  
**Priority:** First — all other tasks depend on this  
**Status:** Pending

---

## Goal

Produce a complete, accurate snapshot of what is currently installed and available on this machine. Update `inventory.md` with real versions. This is the baseline all future tasks will build on.

---

## Instructions

Run the following checks. For each tool, record the version if installed or "not installed" if absent. Do not install anything — this task is observation only.

### System

```bash
uname -a
lsb_release -a
df -h
free -h
```

### Core tools

```bash
git --version
curl --version
wget --version
python3 --version
pip3 --version
java -version 2>&1
node --version
npm --version
```

### Claude Code

```bash
claude --version
```

### Flutter / Android

```bash
flutter --version
flutter doctor
adb --version
which android-studio 2>/dev/null || echo "not found"
```

### Data stack (check if any already installed)

```bash
influx version 2>/dev/null || echo "not installed"
systemctl is-active influxdb 2>/dev/null || echo "influxdb service not found"
grafana-server --version 2>/dev/null || echo "not installed"
systemctl is-active grafana-server 2>/dev/null || echo "grafana service not found"
mosquitto --version 2>/dev/null || echo "not installed"
systemctl is-active mosquitto 2>/dev/null || echo "mosquitto service not found"
```

### Network

```bash
hostname -I
ping -c 1 192.168.110.225 && echo "Pi reachable" || echo "Pi NOT reachable"
```

---

## Deliverables

1. **Update `inventory.md`** — replace the "To verify" table with real findings. Use this format:

```markdown
| Tool | Version | Status |
|------|---------|--------|
| Git | 2.39.2 | ✅ installed |
| Flutter | not found | ❌ needs install |
| InfluxDB | not found | ❌ needs install |
```

2. **Commit and push** with message: `W-001: inventory current tools and environment`

3. **Update `tasks/INDEX.md`** — mark W-001 as Done, add a one-line note (e.g. "Flutter not installed, Python 3.11 available, Pi reachable").

---

## Acceptance criteria

- `inventory.md` contains real version numbers (not "—" or "❓")
- All categories checked (core tools, Flutter/Android, data stack, network)
- Pi reachability confirmed
- Changes committed and pushed

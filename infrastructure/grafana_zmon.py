#!/usr/bin/env python3
"""Create the Grafana datasource 'ZMON-InfluxDB' (Flux, bucket zmon, read-only token) and the dashboard 'zmon-proto1' (4 curves).
Run ON the workstation. The Grafana admin password comes from the environment (GRAFANA_PW), the read token from the file given as argv[1].
Idempotent: an existing datasource is kept, the dashboard is overwritten.
"""
import base64, json, os, sys, urllib.request, urllib.error

G = "http://127.0.0.1:3000"
AUTH = "Basic " + base64.b64encode(("admin:" + os.environ["GRAFANA_PW"]).encode()).decode()
DS_UID = "zmon-influx"


def call(method, path, body=None):
    req = urllib.request.Request(G + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": AUTH, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


st, _ = call("GET", f"/api/datasources/uid/{DS_UID}")
if st == 200:
    print("datasource exists, kept")
else:
    token = open(sys.argv[1]).read().strip()
    st, r = call("POST", "/api/datasources", {
        "name": "ZMON-InfluxDB", "uid": DS_UID, "type": "influxdb", "access": "proxy", "url": "http://localhost:8086",
        "jsonData": {"version": "Flux", "organization": "zax", "defaultBucket": "zmon"}, "secureJsonData": {"token": token}})
    print("datasource create", st, r.get("message", ""))
    if st != 200:
        sys.exit(1)

ds = {"type": "influxdb", "uid": DS_UID}
query = ('from(bucket: "zmon")\n'
         '  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
         '  |> filter(fn: (r) => r._measurement == "zmon" and r._field == "value")\n'
         '  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)')
dash = {"uid": "zmon-proto1", "title": "ZMON prototype 1", "tags": ["zmon"], "timezone": "browser", "schemaVersion": 39,
        "refresh": "10s", "time": {"from": "now-1h", "to": "now"},
        "panels": [{"id": 1, "type": "timeseries", "title": "Temperature (°C), one curve per sensor", "datasource": ds,
                    "gridPos": {"h": 14, "w": 24, "x": 0, "y": 0},
                    "targets": [{"refId": "A", "datasource": ds, "query": query}],
                    "fieldConfig": {"defaults": {"unit": "celsius", "displayName": "${__field.labels.sensor}",
                                                 "custom": {"lineWidth": 1, "spanNulls": 60000}}, "overrides": []},
                    "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["lastNotNull", "min", "max"]}}}]}
st, r = call("POST", "/api/dashboards/db", {"dashboard": dash, "overwrite": True, "message": "zmon prototype 1 (2026-11-22)"})
print("dashboard", st, r.get("status", r.get("message", "")), r.get("url", ""))
sys.exit(0 if st == 200 else 1)

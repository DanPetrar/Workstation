# ANDROID-004 — Config screen

_Completed: 2026-05-27_

---

## flutter analyze

```
Analyzing zax_monitor...
No issues found! (ran in 13.3s)
```

---

## APK build

```
flutter build apk --debug
✓ Built build/app/outputs/flutter-apk/app-debug.apk
```

Build time: ~13 s (Gradle cache warm).

---

## Live /api/config response (Unit_A — 192.168.110.152)

```json
{
  "dev_name": "ZaxEnergy-E47730", "memo": "ZaxEnergy-E47730",
  "ssid": "ZAXSense", "ntp_srv": "pool.ntp.org", "tz_offset": 3,
  "mqtt_en": true, "mqtt_host": "192.168.110.225", "mqtt_port": 1883,
  "mqtt_user": "", "mqtt_topic": "zax_E47730",
  "demo_en": false, "buf_mode": 0, "comm_timeout_s": 10,
  "volt_min": 180, "volt_max": 260, "current_max": 20, "pf_min": 0.5,
  "freq_min": 49.5, "freq_max": 50.5, "ch_mask": 7,
  "fault_mask": 257, "fault_repeat_min": 10
}
```

Fields match the spec exactly. No deviations.

---

## Screen layout

- **Device info card** (read-only): dev_name, ssid, fw_version from sysinfo
- **Device section** (editable): memo, NTP server, TZ offset
- **MQTT section** (editable): enabled switch, broker host, broker port, topic prefix
- **Save button** at bottom; save icon also in AppBar
- Spinner in AppBar while saving; snackbar confirms success or shows error code

POST body sends only the 7 editable fields. Unit restarts or applies config on its side after a successful POST.

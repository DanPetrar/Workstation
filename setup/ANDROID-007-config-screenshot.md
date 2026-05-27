# ANDROID-007 — Config screen screenshot for demo doc

_Completed: 2026-05-27_

---

## Screenshot

Screenshot: `ZaxEnergySurvey/android/screenshots/config.png`

**What the screenshot shows (Unit C — Config):**

| Field | Value |
|-------|-------|
| Screen title | Unit C — Config |
| Device name | ZaxEnergy |
| SSID | ZAXSense |
| Firmware | 1.1.5 |
| NTP server | pool.ntp.org |
| TZ offset | 3 |
| MQTT enabled | Yes (toggle on) |
| Broker host | 192.168.110.225 |

All fields loaded correctly from `/api/config` on Unit C.

---

## Navigation

Tap coordinates used: Unit C gear icon at **x=669, y=375** (Nexus 4, 768×1280).

## Issues

Screen dimmed between the `flutter run` launch and the navigation tap — required an extra `keyevent 26` + `keyevent 82` to wake/unlock before screencap. No other issues.

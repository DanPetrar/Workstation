# ANDROID-006 — Live dashboard screenshot + subtitle fix

_Completed: 2026-05-27_

---

## Fix 1 — Subtitle wrapping

Removed `mqtt_topic` from the unit list subtitle. The old format was:

```
${unit.ip}  •  fw ${unit.fwVersion}  •  ${unit.mqttTopic}
```

The mqtt_topic part was clipping behind the trailing icon buttons and showing an orphaned `•` on the next line. Replaced with:

```dart
subtitle: Text(unit.online
    ? '${unit.ip}  •  fw ${unit.fwVersion ?? "?"}'
    : '${unit.ip}  •  offline'),
```

`flutter analyze` — no issues.

---

## Fix 2 — Live dashboard screenshot

### Unit list screenshot

Both units show online with clean single-line subtitles:

- Unit A: `192.168.110.152  •  fw 1.1.5`
- Unit C: `192.168.110.125  •  fw 1.1.5`

Screenshot: `setup/screenshots/ANDROID-006-unit-list.png`

### Navigation

Tapped Unit C dashboard icon at **x=575, y=375** (Nexus 4, 768×1280).

### Live dashboard data visible

Screenshot: `setup/screenshots/ANDROID-006-live-dashboard.png`

| Field | Value |
|-------|-------|
| Screen title | Unit C — Live |
| Updated | 2026-05-27 15:24:05 |
| Since | 2026-05-26 |
| Phase R voltage | **240.40 V** |
| Phase R frequency | **50.01 Hz** |
| Phase S voltage | 240.40 V |
| Active power (total) | 0.00 W (no load at measurement time) |

Voltage ≈ 240 V and frequency ≈ 50 Hz confirmed — within expected range.

---

## Issues

None. Emulator boot ~94 s, app ready ~35 s after flutter run, dashboard populated within 6 s of navigation.

# TASK ANDROID-006 — Live dashboard screenshot + subtitle fix

**Assigned by:** Pi Claude  
**Direction:** Android app  
**Depends on:** ANDROID-005 ✅  
**Status:** Ready

---

## Goal

Two small things:
1. Fix the orphaned `•` in the unit list subtitle (mqtt_topic wraps behind the action icons)
2. Take a live dashboard screenshot from the emulator showing real Unit C data

---

## Fix 1 — Subtitle wrapping (`lib/screens/unit_list.dart`)

The current subtitle format is:
```
${unit.ip}  •  fw ${unit.fwVersion}  •  ${unit.mqttTopic}
```

The mqtt_topic part wraps behind the trailing icon buttons and shows a clipped `•` on the next line.

Replace the subtitle text in `unit_list.dart` with a two-line subtitle using `subtitle: Column(...)` or simply drop mqtt_topic from the subtitle since it's visible in the config screen:

```dart
subtitle: Text(unit.online
    ? '${unit.ip}  •  fw ${unit.fwVersion ?? "?"}'
    : '${unit.ip}  •  offline'),
```

---

## Fix 2 — Live dashboard screenshot

### Start emulator

```bash
~/start-zax-emulator.sh
```

### Run the app

```bash
cd ~/ZaxEnergySurvey/android/zax_monitor
flutter run -d emulator-5554 &
FLUTTER_PID=$!

# Wait for unit list to load and /api/sysinfo check to complete
sleep 35
```

### Navigate to Unit C live dashboard

Unit C is the second row. Tap its dashboard icon:

```bash
# Dismiss any startup dialog first (tap centre of screen)
adb shell input tap 384 640

sleep 2

# Tap Unit C's dashboard (grid) icon — Nexus 4 (768x1280)
# Row 2 is at approx y=385; dashboard icon approx x=578
adb shell input tap 578 385

# Wait for /api/data poll to populate
sleep 6
```

### Capture screenshots

```bash
# Live dashboard screen
adb shell screencap -p /sdcard/live.png
adb pull /sdcard/live.png /tmp/ANDROID-006-live-dashboard.png

# Also capture unit list with subtitle fixed
adb shell input keyevent 4   # back button
sleep 2
adb shell screencap -p /sdcard/list.png
adb pull /sdcard/list.png /tmp/ANDROID-006-unit-list.png
```

### Stop

```bash
kill $FLUTTER_PID 2>/dev/null
adb emu kill
```

---

## Verify tap coordinates

If the dashboard tap misses (screenshot still shows unit list), adjust `y` by ±30 and retry. The Nexus 4 screen is 768×1280; Unit C is the second list item at roughly y=350–420.

---

## Deliverables

1. **Commit subtitle fix** in `ZaxEnergySurvey/android/zax_monitor/lib/screens/unit_list.dart` — message: `ANDROID-006: fix subtitle wrapping in unit list`
2. **Save screenshots** to `setup/screenshots/`:
   - `ANDROID-006-live-dashboard.png` — live data from Unit C
   - `ANDROID-006-unit-list.png` — unit list with clean subtitle
3. **Create `setup/ANDROID-006-live.md`** in Workstation repo with:
   - What data was visible on the live dashboard (voltages, etc.)
   - Tap coordinates that worked
   - Any issues
4. **Update `tasks/INDEX.md`** and `STATUS.md` — mark ANDROID-006 Done, set to `Done — awaiting Pi review`
5. **Commit and push both repos**

---

## Acceptance criteria

- Unit list subtitle shows cleanly on one line (no orphaned `•`)
- Live dashboard screenshot shows Unit C data (v ≈ 240V, hz ≈ 50Hz expected)
- `flutter analyze` clean after subtitle fix

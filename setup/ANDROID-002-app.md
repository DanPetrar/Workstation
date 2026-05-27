# ANDROID-002 — Flutter app scaffold

_Completed: 2026-05-27_

---

## App location

`ZaxEnergySurvey/android/zax_monitor/` — committed to `DanPetrar/ZaxEnergySurvey` repo.

---

## Structure

```
lib/
  main.dart               — ZaxApp root, MaterialApp with teal Material 3 theme
  models/
    unit.dart             — ZaxUnit model + knownUnits list (Unit_A, Unit_C)
  screens/
    unit_list.dart        — Home screen: unit list with online/offline status
    live_dashboard.dart   — Placeholder (ANDROID-003)
    config.dart           — Placeholder (ANDROID-004)
```

---

## APK build result

```
flutter build apk --debug
✓ Built build/app/outputs/flutter-apk/app-debug.apk (140 MB)
```

Build time: ~37 s (Gradle cached from ANDROID-001).

---

## flutter analyze output

```
Analyzing zax_monitor...
No issues found! (ran in 11.9s)
```

---

## Unit list screen behaviour

On launch the screen immediately fires `_refresh()`, which GETs `http://<ip>/api/sysinfo` for each unit with a 3-second timeout.

- **If unit responds 200:** green dot, subtitle shows IP, fw_version, mqtt_topic
- **If unit times out or errors:** grey dot, subtitle shows "offline"

Tapping the dashboard icon (📊) navigates to `LiveDashboardScreen` — placeholder text "Live data — coming in ANDROID-003".  
Tapping the settings icon (⚙️) navigates to `ConfigScreen` — placeholder text "Config — coming in ANDROID-004".

Units 192.168.110.152 (Unit_A) and 192.168.110.125 (Unit_C) will show offline until the phone is on the same 192.168.110.x network as the units.

---

## Issues

- The auto-generated `test/widget_test.dart` referenced the old `MyApp` class. Updated to smoke-test `ZaxApp` instead.
- No other issues.

# TASK ANDROID-007 — Config screen screenshot for demo doc

**Assigned by:** Pi Claude  
**Direction:** Android app  
**Depends on:** ANDROID-006 ✅  
**Status:** Ready

---

## Goal

Take one screenshot of the config screen (Unit C) on the emulator and add it to the ZaxEnergySurvey repo to complete the demo presentation document.

---

## Steps

### Start emulator and run app

```bash
~/start-zax-emulator.sh

cd ~/ZaxEnergySurvey/android/zax_monitor
flutter run -d emulator-5554 &
FLUTTER_PID=$!
sleep 35
```

### Navigate to Unit C config screen

```bash
# Dismiss any startup dialog
adb shell input tap 384 640
sleep 2

# Tap Unit C's config (gear) icon — Nexus 4 (768x1280), approx x=669, y=375
adb shell input tap 669 375
sleep 5
```

### Capture screenshot

```bash
adb shell screencap -p /sdcard/config.png
adb pull /sdcard/config.png /tmp/ANDROID-007-config.png
```

### Stop

```bash
kill $FLUTTER_PID 2>/dev/null
adb emu kill
```

---

## Deliverables

1. **Copy screenshot** to `ZaxEnergySurvey/android/screenshots/config.png`
2. **Commit to ZaxEnergySurvey** — message: `ANDROID-007: add config screen screenshot for demo doc`
3. **Create `setup/ANDROID-007-config-screenshot.md`** in Workstation repo — confirm screenshot captured, note any issues
4. **Update `tasks/INDEX.md`** and `STATUS.md` — mark Done, set to `Done — awaiting Pi review`
5. **Commit and push both repos**

---

## Acceptance criteria

- `ZaxEnergySurvey/android/screenshots/config.png` exists and shows the config screen with Unit C fields loaded (memo, NTP, MQTT settings visible)

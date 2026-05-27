# TASK ANDROID-005 — Android emulator (headless)

**Assigned by:** Pi Claude  
**Direction:** Android app  
**Depends on:** ANDROID-004 ✅  
**Status:** Ready

---

## Goal

Install a headless Android emulator on the Workstation so future tasks can run, screenshot, and test the app without a physical device.

---

## Step 1 — Check KVM availability

```bash
kvm-ok
ls /dev/kvm
```

If `kvm-ok` is not installed: `sudo apt-get install -y cpu-checker`.

**If KVM is NOT available:** stop here, report in `setup/ANDROID-005-emulator.md`, and mark Done — the emulator is impractical without it. Pi will decide next steps.

**If KVM is available:** continue.

```bash
# Add current user to kvm group (avoids sudo for emulator)
sudo usermod -aG kvm $USER
# Apply without logout:
newgrp kvm
```

---

## Step 2 — Install emulator and system image

```bash
sdkmanager "emulator" \
  "system-images;android-36;google_apis;x86_64"
```

Also install any missing platform tools:

```bash
sdkmanager "platform-tools"
```

Accept licenses if prompted:

```bash
yes | sdkmanager --licenses
```

---

## Step 3 — Create AVD

```bash
echo no | avdmanager create avd \
  --name zax_test \
  --package "system-images;android-36;google_apis;x86_64" \
  --device "pixel_6"

avdmanager list avd
```

Expected: `zax_test` appears in the list with no errors.

---

## Step 4 — Start emulator headlessly

```bash
# Start in background — takes 60–120 s to boot fully
$ANDROID_HOME/emulator/emulator \
  -avd zax_test \
  -no-window \
  -no-audio \
  -gpu swiftshader_indirect \
  -no-snapshot \
  &

# Wait for full boot
adb wait-for-device
adb shell 'while [[ -z $(getprop sys.boot_completed) ]]; do sleep 3; done; echo booted'
```

Expected: `booted` printed within 3 minutes.

```bash
adb devices
```

Expected: one device listed as `emulator-5554  device`.

---

## Step 5 — Run the app and capture a screenshot

```bash
cd ~/ZaxEnergySurvey/android/zax_monitor

# Run in background, wait for it to launch
flutter run -d emulator-5554 &
FLUTTER_PID=$!
sleep 30

# Capture unit list screen
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png /tmp/zax-unit-list.png

# Stop flutter
kill $FLUTTER_PID 2>/dev/null
```

Save the screenshot as `setup/screenshots/ANDROID-005-unit-list.png` in this repo.

The unit list will show both units as **offline** (emulator is on a different network segment from the units) — that is expected and correct.

---

## Step 6 — Stop emulator

```bash
adb emu kill
```

---

## Emulator startup helper

Add a convenience script at `~/start-zax-emulator.sh`:

```bash
#!/bin/bash
$ANDROID_HOME/emulator/emulator \
  -avd zax_test \
  -no-window \
  -no-audio \
  -gpu swiftshader_indirect \
  -no-snapshot \
  &
echo "Waiting for boot..."
adb wait-for-device
adb shell 'while [[ -z $(getprop sys.boot_completed) ]]; do sleep 3; done; echo booted'
echo "Emulator ready. ADB: $(adb devices | grep emulator)"
```

```bash
chmod +x ~/start-zax-emulator.sh
```

Future tasks start the emulator with `~/start-zax-emulator.sh`.

---

## Deliverables

1. **Save screenshot** `setup/screenshots/ANDROID-005-unit-list.png`
2. **Create `setup/ANDROID-005-emulator.md`** with:
   - KVM check result
   - `avdmanager list avd` output
   - `adb devices` output after boot
   - Screenshot path (or note if app failed to launch)
   - Boot time (seconds from emulator start to `booted`)
   - Any issues
3. **Update `inventory.md`** — add emulator row to data stack section (AVD name, API level, status)
4. **Update `tasks/INDEX.md`** and `STATUS.md` — mark ANDROID-005 Done, set to `Done — awaiting Pi review`
5. **Commit and push** — message: `ANDROID-005: headless Android emulator installed and verified`

---

## Acceptance criteria

- KVM available (if not, report and stop — still mark Done)
- `adb devices` shows `emulator-5554  device`
- App launches and screenshot captured (unit list visible, both units offline is fine)
- Boot time under 3 minutes

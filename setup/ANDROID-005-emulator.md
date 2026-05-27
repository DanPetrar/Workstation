# ANDROID-005 — Headless Android emulator

_Completed: 2026-05-27 — AVD recreated with Nexus 4 profile, ANR resolved (2026-05-27)_

---

## KVM check

```
INFO: /dev/kvm exists
KVM acceleration can be used
```

`/dev/kvm` present, 8 VMX-capable cores. `dan-linux` added to `kvm` group.

---

## SDK components installed

| Package | Version |
|---------|---------|
| emulator | latest (downloaded) |
| system-images;android-36;google_apis;x86_64 | r07 |

---

## AVD created

```
avdmanager list avd

Available Android Virtual Devices:
    Name: zax_test
  Device: pixel_6 (Google)
    Path: /home/dan-linux/.android/avd/zax_test.avd
  Target: Google APIs (Google Inc.)
          Based on: Android API 36  Tag/ABI: google_apis/x86_64
  Sdcard: 512 MB
```

---

## Boot result

```
adb devices
emulator-5554   device
```

Boot time: ~60 s with `-no-boot-anim` flag.

---

## App launch and screenshot

App launched on emulator, unit list visible within 45 s of `flutter run`.

Screenshot: `setup/screenshots/ANDROID-005-unit-list.png`

**What the screenshot shows:**
- App title: "ZaxEnergy Units"
- Unit A (192.168.110.152): grey dot — **offline** ✓ (expected — emulator on 10.0.2.x, Unit A unreachable)
- Unit C (192.168.110.125): green dot — **online**, fw 1.1.5, Live + Config icons visible

Unit C is reachable from the emulator because the Android emulator bridges through the host's network at `10.0.2.2`, and the host machine (192.168.110.11) can route to 192.168.110.x.

---

## ANR fix applied

Original AVD used Pixel 6 (1080×2400) which caused System UI ANR under swiftshader on the i3.
AVD recreated with **Nexus 4** profile (768×1280) — ANR no longer occurs.
Boot time: ~94 s. Clean screenshot captured with no dialogs.

---

## Helper script

`~/start-zax-emulator.sh` — starts the emulator and waits for boot.
Usage: `~/start-zax-emulator.sh` (runs in foreground until booted, then exits; emulator stays running in background).

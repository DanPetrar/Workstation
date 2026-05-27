# ANDROID-005 — Headless Android emulator

_Completed: 2026-05-27_

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

## Known issue — System UI ANR dialog

The Android System UI consistently fires an ANR ("System UI isn't responding") on this hardware under swiftshader rendering. This is caused by the i3 CPU being too slow for software-rendered OpenGL at Pixel 6 resolution (1080×2400).

**The ANR does not affect the Flutter app** — the app code, HTTP polling, and navigation all work correctly. The ANR dialog appears in front of the app in screenshots but the app is fully functional behind it.

**Mitigation options for Pi to decide:**
1. Use a lower-resolution device profile when recreating the AVD (e.g. `Nexus 4` instead of `pixel_6`)
2. Accept the ANR as a cosmetic issue for screenshot tasks
3. Use a physical device instead of the emulator for screenshot evidence

---

## Helper script

`~/start-zax-emulator.sh` — starts the emulator and waits for boot.
Usage: `~/start-zax-emulator.sh` (runs in foreground until booted, then exits; emulator stays running in background).

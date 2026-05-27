# ANDROID-001 — Flutter + Java + Android SDK setup

_Completed: 2026-05-27_

---

## Flutter

| Item | Value |
|------|-------|
| Version | 3.44.0 |
| Channel | stable |
| Install path | `/opt/flutter` |
| Dart version | 3.12.0 |
| DevTools | 2.57.0 |

---

## Java

| Item | Value |
|------|-------|
| Version | OpenJDK 17.0.18 |
| Package | `openjdk-17-jdk` (via apt) |
| Binary | `/usr/bin/java` |

---

## Android SDK

| Item | Value |
|------|-------|
| ANDROID_HOME | `/home/dan-linux/Android/Sdk` |
| cmdline-tools | `latest` (11076708) |
| platform-tools | 37.0.0 (adb) |
| platforms | android-34, android-36 |
| build-tools | 34.0.0, 36.0.0 |
| cmake | 3.22.1 |
| NDK | 28.2.13676358 |

> Note: Task spec targeted API 34, but Flutter 3.44.0 requires API 36 minimum. API 36 + build-tools 36.0.0 were installed in addition to 34.

---

## flutter doctor -v output

```
[✓] Flutter (Channel stable, 3.44.0, on Ubuntu 26.04 LTS 7.0.0-15-generic, locale en_US.UTF-8)
    • Flutter version 3.44.0 on channel stable at /opt/flutter
    • Dart version 3.12.0
    • DevTools version 2.57.0

[✓] Android toolchain - develop for Android devices (Android SDK version 36.0.0)
    • Android SDK at /home/dan-linux/Android/Sdk
    • Platform android-36, build-tools 36.0.0
    • Java version OpenJDK Runtime Environment (build 17.0.18+8-Ubuntu-1)
    • All Android licenses accepted.

[✗] Chrome - not installed (not needed for Android builds)
[✗] Linux toolchain - clang/GTK not installed (not needed for Android builds)

[✓] Connected device (1 available)
[✓] Network resources
```

---

## APK build test

```
cd /tmp && flutter create hello_zax
cd hello_zax && flutter build apk --debug
✓ Built build/app/outputs/flutter-apk/app-debug.apk (140 MB)
```

Build succeeded. Project cleaned up.

---

## PATH additions (in ~/.bashrc)

```bash
export PATH="$PATH:/opt/flutter/bin"
export ANDROID_HOME=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

To activate in the current shell: `source ~/.bashrc`

---

## Issues

- Flutter 3.44.0 stable requires Android SDK platform 36, not 34 as the task spec stated. Both API 34 and API 36 are now installed.
- Chrome and Linux desktop toolchain are absent — neither is needed for Android APK builds.

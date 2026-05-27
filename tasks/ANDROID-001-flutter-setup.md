# TASK ANDROID-001 — Setup Flutter + Java environment

**Assigned by:** Pi Claude  
**Direction:** Android app  
**Depends on:** nothing  
**Status:** Ready

---

## Goal

Install Flutter SDK and Java (JDK) on the Workstation so the ZaxEnergy Android demo app can be built. No Android Studio needed — command-line tools only.

---

## Target versions

| Tool | Target |
|------|--------|
| Flutter | stable channel, latest (3.x) |
| Java (JDK) | 17 (LTS, required by Flutter/Gradle) |
| Android SDK | command-line tools only (no Studio) |
| Android build-tools | 34.x |
| Android platform | API 34 |

---

## Step 1 — Install Java 17

```bash
sudo apt-get update
sudo apt-get install -y openjdk-17-jdk
java -version
```

Expected: `openjdk version "17.x.x"`.

---

## Step 2 — Install Flutter SDK

```bash
cd /opt
sudo git clone https://github.com/flutter/flutter.git -b stable --depth 1
sudo chown -R $USER:$USER /opt/flutter
export PATH="$PATH:/opt/flutter/bin"
flutter --version
```

Add to `~/.bashrc` so it persists:

```bash
echo 'export PATH="$PATH:/opt/flutter/bin"' >> ~/.bashrc
```

---

## Step 3 — Install Android command-line tools

```bash
mkdir -p ~/Android/Sdk/cmdline-tools
cd ~/Android/Sdk/cmdline-tools

# Download latest cmdline-tools (check https://developer.android.com/studio for current URL)
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip commandlinetools-linux-11076708_latest.zip
mv cmdline-tools latest
rm commandlinetools-linux-11076708_latest.zip
```

Add to `~/.bashrc`:

```bash
cat >> ~/.bashrc << 'EOF'
export ANDROID_HOME=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools
EOF
source ~/.bashrc
```

---

## Step 4 — Accept licenses and install SDK components

```bash
yes | sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
```

---

## Step 5 — Run flutter doctor

```bash
flutter doctor
```

Expected output (✅ required, ⚠️ acceptable for items not needed):

```
[✓] Flutter
[✓] Android toolchain
[✓] Linux toolchain   (or ✗ — not needed for Android builds)
[✗] Android Studio    (acceptable — not installing Studio)
[✗] VS Code           (acceptable)
[✓] Connected device  (will show "no devices" — acceptable at this stage)
```

The key requirement: **Flutter** and **Android toolchain** both green.

---

## Step 6 — Verify a build is possible

```bash
cd /tmp
flutter create hello_zax
cd hello_zax
flutter build apk --debug 2>&1 | tail -5
```

Expected: `✓ Built build/app/outputs/flutter-apk/app-debug.apk`.

```bash
ls -lh build/app/outputs/flutter-apk/app-debug.apk
```

Clean up:

```bash
cd /tmp && rm -rf hello_zax
```

---

## Deliverables

1. **Create `setup/ANDROID-001-flutter.md`** with:
   - Flutter version (`flutter --version` output)
   - Java version
   - Android SDK path and installed components (`sdkmanager --list_installed`)
   - `flutter doctor` output (full)
   - APK build result
   - Any issues

2. **Update `inventory.md`** — fill in Flutter SDK, Java, Android SDK rows (currently all ❌)

3. **Update `tasks/INDEX.md`** and `STATUS.md` — mark ANDROID-001 Done, set status to `Done — awaiting Pi review`

4. **Commit and push** — message: `ANDROID-001: Flutter + Java + Android SDK installed`

---

## Acceptance criteria

- `flutter doctor` shows Flutter ✅ and Android toolchain ✅
- `flutter build apk --debug` succeeds on a blank project
- Versions recorded in `setup/ANDROID-001-flutter.md`

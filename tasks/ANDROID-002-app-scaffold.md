# TASK ANDROID-002 — Flutter app scaffold

**Assigned by:** Pi Claude  
**Direction:** Android app  
**Depends on:** ANDROID-001 ✅  
**Status:** Ready

---

## Goal

Create the ZaxEnergy Flutter demo app in the ZaxEnergySurvey repo. Implement a 3-screen navigation skeleton with a live unit list that shows online/offline status by querying each unit's `/api/sysinfo`. No data panels yet — just structure, navigation, and connectivity check.

---

## Context

| Item | Value |
|------|-------|
| Repo | `git@github.com:DanPetrar/ZaxEnergySurvey.git` |
| App location | `android/zax_monitor/` |
| Flutter | 3.44.0 stable at `/opt/flutter` |
| Known units | Unit_A → `192.168.110.152`, Unit_C → `192.168.110.125` |
| Unit API | `GET http://<ip>/api/sysinfo` — returns JSON with `fw_version`, `unit_name`, `mqtt_topic`, etc. |
| Target | Android APK (WiFi REST only, no BLE, no Play Store) |

---

## Step 1 — Clone repo and create project

```bash
cd ~
git clone git@github.com:DanPetrar/ZaxEnergySurvey.git
cd ZaxEnergySurvey/android

flutter create zax_monitor \
  --org eu.zapptronic \
  --project-name zax_monitor \
  --platforms android
```

---

## Step 2 — Add HTTP dependency

In `android/zax_monitor/pubspec.yaml`, add under `dependencies`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.0
```

Then:

```bash
cd android/zax_monitor
flutter pub get
```

---

## Step 3 — App structure

Replace `lib/` with the following files:

**`lib/main.dart`**
```dart
import 'package:flutter/material.dart';
import 'screens/unit_list.dart';

void main() => runApp(const ZaxApp());

class ZaxApp extends StatelessWidget {
  const ZaxApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ZaxEnergy',
      theme: ThemeData(colorSchemeSeed: Colors.teal, useMaterial3: true),
      home: const UnitListScreen(),
    );
  }
}
```

**`lib/models/unit.dart`**
```dart
class ZaxUnit {
  final String name;
  final String ip;
  bool online;
  String? fwVersion;
  String? mqttTopic;

  ZaxUnit({required this.name, required this.ip, this.online = false});
}

final List<ZaxUnit> knownUnits = [
  ZaxUnit(name: 'Unit A', ip: '192.168.110.152'),
  ZaxUnit(name: 'Unit C', ip: '192.168.110.125'),
];
```

**`lib/screens/unit_list.dart`**
```dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../models/unit.dart';
import 'live_dashboard.dart';
import 'config.dart';

class UnitListScreen extends StatefulWidget {
  const UnitListScreen({super.key});

  @override
  State<UnitListScreen> createState() => _UnitListScreenState();
}

class _UnitListScreenState extends State<UnitListScreen> {
  bool _loading = false;

  Future<void> _refresh() async {
    setState(() => _loading = true);
    for (final unit in knownUnits) {
      try {
        final res = await http
            .get(Uri.parse('http://${unit.ip}/api/sysinfo'))
            .timeout(const Duration(seconds: 3));
        if (res.statusCode == 200) {
          final j = jsonDecode(res.body);
          unit.online = true;
          unit.fwVersion = j['fw_version'];
          unit.mqttTopic = j['mqtt_topic'];
        } else {
          unit.online = false;
        }
      } catch (_) {
        unit.online = false;
      }
    }
    setState(() => _loading = false);
  }

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ZaxEnergy Units'),
        actions: [
          if (_loading)
            const Padding(
              padding: EdgeInsets.all(16),
              child: SizedBox(width: 20, height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2)),
            )
          else
            IconButton(icon: const Icon(Icons.refresh), onPressed: _refresh),
        ],
      ),
      body: ListView.builder(
        itemCount: knownUnits.length,
        itemBuilder: (ctx, i) {
          final unit = knownUnits[i];
          return ListTile(
            leading: Icon(Icons.circle,
                color: unit.online ? Colors.green : Colors.grey, size: 14),
            title: Text(unit.name),
            subtitle: Text(unit.online
                ? '${unit.ip}  •  fw ${unit.fwVersion ?? "?"}  •  ${unit.mqttTopic ?? ""}'
                : '${unit.ip}  •  offline'),
            trailing: unit.online
                ? Row(mainAxisSize: MainAxisSize.min, children: [
                    IconButton(
                      icon: const Icon(Icons.dashboard),
                      tooltip: 'Live',
                      onPressed: () => Navigator.push(ctx,
                          MaterialPageRoute(
                              builder: (_) => LiveDashboardScreen(unit: unit))),
                    ),
                    IconButton(
                      icon: const Icon(Icons.settings),
                      tooltip: 'Config',
                      onPressed: () => Navigator.push(ctx,
                          MaterialPageRoute(
                              builder: (_) => ConfigScreen(unit: unit))),
                    ),
                  ])
                : null,
          );
        },
      ),
    );
  }
}
```

**`lib/screens/live_dashboard.dart`**
```dart
import 'package:flutter/material.dart';
import '../models/unit.dart';

class LiveDashboardScreen extends StatelessWidget {
  final ZaxUnit unit;
  const LiveDashboardScreen({super.key, required this.unit});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('${unit.name} — Live')),
      body: const Center(child: Text('Live data — coming in ANDROID-003')),
    );
  }
}
```

**`lib/screens/config.dart`**
```dart
import 'package:flutter/material.dart';
import '../models/unit.dart';

class ConfigScreen extends StatelessWidget {
  final ZaxUnit unit;
  const ConfigScreen({super.key, required this.unit});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('${unit.name} — Config')),
      body: const Center(child: Text('Config — coming in ANDROID-004')),
    );
  }
}
```

---

## Step 4 — Build and verify

```bash
cd ~/ZaxEnergySurvey/android/zax_monitor
flutter build apk --debug 2>&1 | tail -5
ls -lh build/app/outputs/flutter-apk/app-debug.apk
```

Expected: APK built successfully.

---

## Step 5 — Run flutter analyze

```bash
flutter analyze
```

Expected: no errors (warnings about placeholder screens are acceptable).

---

## Deliverables

1. **Commit the Flutter project** to `ZaxEnergySurvey/android/zax_monitor/` — add a `.gitignore` (use `flutter create`'s default). Do **not** commit `build/` or `.dart_tool/`.
2. **Create `setup/ANDROID-002-app.md`** in the Workstation repo with:
   - APK build result
   - `flutter analyze` output
   - Screenshot or description of unit list screen (online/offline status of Unit_A and Unit_C)
3. **Update `tasks/INDEX.md`** and `STATUS.md` — mark ANDROID-002 Done, set status to `Done — awaiting Pi review`
4. **Commit and push both repos** — Workstation repo message: `ANDROID-002: Flutter app scaffold with unit list`; ZaxEnergySurvey message: `ANDROID-002: Flutter app scaffold — unit list, nav skeleton`

---

## Acceptance criteria

- `flutter build apk --debug` succeeds
- `flutter analyze` clean
- App shows Unit A and Unit C in the list with online/offline status
- Tapping Live or Config navigates to placeholder screens
- `android/zax_monitor/` committed to ZaxEnergySurvey repo

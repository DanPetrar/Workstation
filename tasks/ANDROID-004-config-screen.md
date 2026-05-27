# TASK ANDROID-004 — Config screen

**Assigned by:** Pi Claude  
**Direction:** Android app  
**Depends on:** ANDROID-003 ✅  
**Status:** Ready

---

## Goal

Implement the `ConfigScreen` — replace the placeholder with a screen that reads `/api/config`, displays editable fields, and saves changes via `POST /api/config`.

---

## Context

| Item | Value |
|------|-------|
| App | `ZaxEnergySurvey/android/zax_monitor/` |
| GET endpoint | `GET http://<ip>/api/config` |
| POST endpoint | `POST http://<ip>/api/config` with JSON body |
| File to replace | `lib/screens/config.dart` |

### Real `/api/config` GET response

Queried live from Unit_A (192.168.110.152):

```json
{
  "dev_name":        "ZaxEnergy-E47730",
  "memo":            "ZaxEnergy-E47730",
  "ssid":            "ZAXSense",
  "ntp_srv":         "pool.ntp.org",
  "tz_offset":       3,
  "mqtt_en":         true,
  "mqtt_host":       "192.168.110.225",
  "mqtt_port":       1883,
  "mqtt_user":       "",
  "mqtt_topic":      "zax_E47730",
  "demo_en":         false,
  "buf_mode":        0,
  "comm_timeout_s":  10,
  "volt_min":        180,  "volt_max":   260,
  "current_max":     20,
  "pf_min":          0.5,
  "freq_min":        49.5, "freq_max":   50.5,
  "ch_mask":         7,
  "fault_mask":      257,
  "fault_repeat_min": 10
}
```

---

## Fields to expose in the UI

Show only the fields a user would realistically change. Group them into two sections:

**Device**
- `memo` — text (display name / label)
- `tz_offset` — integer (UTC offset hours, e.g. 3)
- `ntp_srv` — text (NTP server)

**MQTT**
- `mqtt_en` — boolean switch
- `mqtt_host` — text (broker IP/hostname)
- `mqtt_port` — integer
- `mqtt_topic` — text (topic prefix)

Read-only display (no editing): `dev_name`, `ssid`, `fw_version` from `/api/sysinfo`.

---

## Implementation

Replace `lib/screens/config.dart` with:

```dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../models/unit.dart';

class ConfigScreen extends StatefulWidget {
  final ZaxUnit unit;
  const ConfigScreen({super.key, required this.unit});

  @override
  State<ConfigScreen> createState() => _ConfigScreenState();
}

class _ConfigScreenState extends State<ConfigScreen> {
  Map<String, dynamic>? _cfg;
  bool _loading = true;
  bool _saving = false;
  String? _error;

  late TextEditingController _memo;
  late TextEditingController _ntpSrv;
  late TextEditingController _tzOffset;
  late TextEditingController _mqttHost;
  late TextEditingController _mqttPort;
  late TextEditingController _mqttTopic;
  bool _mqttEn = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _memo.dispose(); _ntpSrv.dispose(); _tzOffset.dispose();
    _mqttHost.dispose(); _mqttPort.dispose(); _mqttTopic.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await http
          .get(Uri.parse('http://${widget.unit.ip}/api/config'))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        final j = jsonDecode(res.body) as Map<String, dynamic>;
        setState(() {
          _cfg = j;
          _memo     = TextEditingController(text: j['memo']?.toString() ?? '');
          _ntpSrv   = TextEditingController(text: j['ntp_srv']?.toString() ?? '');
          _tzOffset = TextEditingController(text: j['tz_offset']?.toString() ?? '0');
          _mqttHost = TextEditingController(text: j['mqtt_host']?.toString() ?? '');
          _mqttPort = TextEditingController(text: j['mqtt_port']?.toString() ?? '1883');
          _mqttTopic= TextEditingController(text: j['mqtt_topic']?.toString() ?? '');
          _mqttEn   = j['mqtt_en'] == true;
          _loading  = false;
        });
      } else {
        setState(() { _error = 'HTTP ${res.statusCode}'; _loading = false; });
      }
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final body = {
      'memo':       _memo.text,
      'ntp_srv':    _ntpSrv.text,
      'tz_offset':  int.tryParse(_tzOffset.text) ?? 0,
      'mqtt_en':    _mqttEn,
      'mqtt_host':  _mqttHost.text,
      'mqtt_port':  int.tryParse(_mqttPort.text) ?? 1883,
      'mqtt_topic': _mqttTopic.text,
    };
    try {
      final res = await http
          .post(
            Uri.parse('http://${widget.unit.ip}/api/config'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 5));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(res.statusCode == 200 ? 'Saved' : 'Error ${res.statusCode}'),
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Save failed: $e')));
      }
    }
    setState(() => _saving = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.unit.name} — Config'),
        actions: [
          if (_saving)
            const Padding(
              padding: EdgeInsets.all(16),
              child: SizedBox(width: 20, height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2)),
            )
          else if (_cfg != null)
            IconButton(
              icon: const Icon(Icons.save),
              tooltip: 'Save',
              onPressed: _save,
            ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text('Error: $_error'))
              : _buildForm(),
    );
  }

  Widget _buildForm() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Read-only info
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Device info',
                  style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 8),
              _info('Name',  _cfg!['dev_name']?.toString() ?? '—'),
              _info('SSID',  _cfg!['ssid']?.toString() ?? '—'),
              _info('fw',    widget.unit.fwVersion ?? '—'),
            ]),
          ),
        ),
        const SizedBox(height: 12),
        // Editable: Device
        Text('Device', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        _field('Memo / label', _memo),
        _field('NTP server', _ntpSrv),
        _field('TZ offset (hours)', _tzOffset, numeric: true),
        const SizedBox(height: 16),
        // Editable: MQTT
        Text('MQTT', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        SwitchListTile(
          title: const Text('MQTT enabled'),
          value: _mqttEn,
          onChanged: (v) => setState(() => _mqttEn = v),
          contentPadding: EdgeInsets.zero,
        ),
        _field('Broker host', _mqttHost),
        _field('Broker port', _mqttPort, numeric: true),
        _field('Topic prefix', _mqttTopic),
        const SizedBox(height: 24),
        FilledButton.icon(
          onPressed: _saving ? null : _save,
          icon: const Icon(Icons.save),
          label: const Text('Save'),
        ),
      ],
    );
  }

  Widget _info(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          children: [
            SizedBox(
                width: 80,
                child: Text(label,
                    style: const TextStyle(color: Colors.grey))),
            Expanded(child: Text(value)),
          ],
        ),
      );

  Widget _field(String label, TextEditingController ctrl,
      {bool numeric = false}) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextField(
          controller: ctrl,
          decoration: InputDecoration(
            labelText: label,
            border: const OutlineInputBorder(),
            isDense: true,
          ),
          keyboardType:
              numeric ? TextInputType.number : TextInputType.text,
        ),
      );
}
```

---

## Verify

```bash
cd ~/ZaxEnergySurvey/android/zax_monitor
flutter analyze
flutter build apk --debug 2>&1 | tail -3
```

Both must pass cleanly.

---

## Deliverables

1. **Commit updated `lib/screens/config.dart`** to ZaxEnergySurvey — message: `ANDROID-004: config screen reads and saves /api/config`
2. **Create `setup/ANDROID-004-config.md`** in Workstation repo with:
   - `flutter analyze` output
   - APK build result
   - Observed GET response from a live unit (confirm fields match spec above)
   - Any deviations
3. **Update `tasks/INDEX.md`** and `STATUS.md` — mark ANDROID-004 Done, set to `Done — awaiting Pi review`
4. **Commit and push both repos**

---

## Acceptance criteria

- `flutter analyze` clean
- APK builds
- Config screen loads fields from `/api/config` and save button posts them back

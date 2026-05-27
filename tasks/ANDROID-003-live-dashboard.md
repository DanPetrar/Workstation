# TASK ANDROID-003 — Live dashboard screen

**Assigned by:** Pi Claude  
**Direction:** Android app  
**Depends on:** ANDROID-002 ✅  
**Status:** Ready

---

## Goal

Implement the `LiveDashboardScreen` — replace the placeholder with a screen that polls `/api/data` every 2 seconds and displays per-phase power measurements for the selected unit.

---

## Context

| Item | Value |
|------|-------|
| App | `ZaxEnergySurvey/android/zax_monitor/` |
| Endpoint | `GET http://<unit-ip>/api/data` |
| Poll interval | 2 seconds |
| File to replace | `lib/screens/live_dashboard.dart` |

### `/api/data` response shape (relevant fields)

```json
{
  "v":   [238.5, 239.1, 240.0],
  "a":   [1.23,  0.95,  1.10],
  "w":   [293.4, 226.8, 263.9],
  "hz":  [50.01, 50.01, 50.01],
  "pf":  [0.998, 0.997, 0.999],
  "var": [12, -8, 5],
  "kwh":  [14.21, 12.05, 13.87],
  "kvarh": [0.41, 0.22, 0.31],
  "total_w":   784.1,
  "total_kwh": 40.13,
  "energy_since": "2026-05-20T08:00:00Z"
}
```

Arrays are indexed `[R, S, T]` (index 0, 1, 2).

---

## Implementation

Replace `lib/screens/live_dashboard.dart` with:

```dart
import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../models/unit.dart';

class LiveDashboardScreen extends StatefulWidget {
  final ZaxUnit unit;
  const LiveDashboardScreen({super.key, required this.unit});

  @override
  State<LiveDashboardScreen> createState() => _LiveDashboardScreenState();
}

class _LiveDashboardScreenState extends State<LiveDashboardScreen> {
  Timer? _timer;
  Map<String, dynamic>? _data;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetch();
    _timer = Timer.periodic(const Duration(seconds: 2), (_) => _fetch());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetch() async {
    try {
      final res = await http
          .get(Uri.parse('http://${widget.unit.ip}/api/data'))
          .timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        setState(() {
          _data = jsonDecode(res.body);
          _error = null;
        });
      }
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('${widget.unit.name} — Live')),
      body: _error != null
          ? Center(child: Text('Error: $_error'))
          : _data == null
              ? const Center(child: CircularProgressIndicator())
              : _buildDashboard(),
    );
  }

  Widget _buildDashboard() {
    final d = _data!;
    final phases = ['R', 'S', 'T'];

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _summaryCard(d),
        const SizedBox(height: 12),
        for (var i = 0; i < 3; i++) _phaseCard(phases[i], i, d),
      ],
    );
  }

  Widget _summaryCard(Map<String, dynamic> d) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Total', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          _row('Active power', '${_fmt(d['total_w'])} W'),
          _row('Energy (session)', '${_fmt(d['total_kwh'])} kWh'),
          if (d['energy_since'] != null)
            _row('Since', d['energy_since'].toString().substring(0, 10)),
        ]),
      ),
    );
  }

  Widget _phaseCard(String phase, int i, Map<String, dynamic> d) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Phase $phase',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          _row('Voltage',  '${_fmt(_idx(d['v'],  i))} V'),
          _row('Current',  '${_fmt(_idx(d['a'],  i))} A'),
          _row('Power',    '${_fmt(_idx(d['w'],  i))} W'),
          _row('Freq',     '${_fmt(_idx(d['hz'], i))} Hz'),
          _row('PF',       _fmt(_idx(d['pf'], i))),
          _row('VAr',      '${_idx(d['var'], i)}'),
        ]),
      ),
    );
  }

  Widget _row(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(color: Colors.grey)),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w500)),
          ],
        ),
      );

  String _fmt(dynamic v) =>
      v == null ? '—' : (v as num).toStringAsFixed(2);

  dynamic _idx(dynamic list, int i) =>
      (list is List && list.length > i) ? list[i] : null;
}
```

---

## Verify

```bash
cd ~/ZaxEnergySurvey/android/zax_monitor
flutter analyze
flutter build apk --debug 2>&1 | tail -3
```

Both must pass cleanly. If your phone is on the 192.168.110.x network and the app is installed, test with a real unit — otherwise `flutter analyze` + APK build is sufficient for this task.

---

## Deliverables

1. **Commit updated `lib/screens/live_dashboard.dart`** to ZaxEnergySurvey repo — message: `ANDROID-003: live dashboard screen polls /api/data`
2. **Create `setup/ANDROID-003-live.md`** in Workstation repo with:
   - `flutter analyze` output
   - APK build result
   - Any deviations from the spec (e.g. `/api/data` response fields that differ from the spec above)
3. **Update `tasks/INDEX.md`** and `STATUS.md` — mark ANDROID-003 Done, set to `Done — awaiting Pi review`
4. **Commit and push both repos**

---

## Acceptance criteria

- `flutter analyze` clean
- APK builds successfully
- `live_dashboard.dart` no longer shows placeholder text

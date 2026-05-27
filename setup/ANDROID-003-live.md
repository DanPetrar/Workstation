# ANDROID-003 — Live dashboard screen

_Completed: 2026-05-27_

---

## flutter analyze

```
Analyzing zax_monitor...
No issues found! (ran in 13.9s)
```

---

## APK build

```
flutter build apk --debug
✓ Built build/app/outputs/flutter-apk/app-debug.apk
```

Build time: ~14 s (Gradle cache warm).

---

## API shape deviation — actual vs spec

Both units were reachable during implementation. The actual `/api/data` response
differs significantly from the spec shape:

**Spec assumed:**
```json
{ "v": [238.5, 239.1, 240.0], "a": [...], ... }
```
Flat arrays indexed [R, S, T] at the top level.

**Actual response:**
```json
{
  "dev_name": "ZaxEnergy-E47730",
  "total_w": 0, "total_kwh": 0, "total_kvarh": 0,
  "energy_since": 1779830226,
  "ts_str": "2026-05-27 14:24:52",
  "sec": {
    "R": {"v": 239.7, "a": 0, "w": 0, "var": 0, "pf": 0, "hz": 50.02},
    "S": {"v": 240.2, "a": 0, "w": 0, "var": 0, "pf": 0, "hz": 50.02},
    "T": {"v": 240.3, "a": 0, "w": 0, "var": 0, "pf": 0, "hz": 50.02}
  },
  "min": {
    "R": {"kwh": 0, "kvarh": 0},
    "S": {"kwh": 0, "kvarh": 0},
    "T": {"kwh": 0, "kvarh": 0}
  }
}
```

Key differences:
- Phase data nested under `sec` (per-second) and `min` (per-minute) objects, keyed by `"R"/"S"/"T"`
- `energy_since` is a Unix timestamp integer, not an ISO string
- `total_kvarh` present (spec omitted it)
- `ts_str` field gives last measurement timestamp

Implementation uses the actual shape. The `_phaseCard` helper receives `sec[phase]` and `min[phase]` maps directly.

---

## Live data observed

Both units responding at implementation time:
- Unit_A (192.168.110.152): v ≈ 239–240 V, hz = 50.02, a/w/var = 0 (no load)
- Unit_C (192.168.110.125): same voltage range, one phase showed a = 0.03 A

---

## Screen layout

- **Total card**: active power (W), energy session (kWh + kVArh), since date, last updated timestamp
- **Phase R/S/T cards** (one each): V, A, W, Hz, PF, VAr, kWh, kVArh
- Polling every 2 s via `Timer.periodic`; spinner shown until first response; error message if request fails

#!/usr/bin/env python3
"""Length-dispatch check for zaxmodbus_parser (W2).

Run:  python3 infrastructure/test_zaxmodbus_parser.py

Stubs paho/influxdb_client so the pure decode functions can be exercised with
no broker, no database and no network — the parser module builds its Influx
client at import time.
"""
import os, struct, sys, types

for name in ("paho", "paho.mqtt", "paho.mqtt.client",
             "influxdb_client", "influxdb_client.client",
             "influxdb_client.client.write_api"):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules["influxdb_client"].InfluxDBClient = lambda **k: types.SimpleNamespace(
    write_api=lambda **kk: types.SimpleNamespace(write=lambda **kkk: None))
sys.modules["influxdb_client.client.write_api"].SYNCHRONOUS = object()

import tempfile
_tok = tempfile.NamedTemporaryFile("w", suffix=".token", delete=False)
_tok.write("test-token"); _tok.close()
os.environ["ZAX_TOKEN_FILE"] = _tok.name

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zaxmodbus_parser as P
os.unlink(_tok.name)

TS = 1_767_225_600            # a plausible epoch, well past the 2020 floor
IMP_KWH   = (1.5, 2.5, 3.5)
IMP_KVARH = (0.1, 0.2, 0.3)
EXP_KWH   = (10.5, 20.5, 30.5)
EXP_KVARH = (1.1, 2.2, 3.3)

v1 = struct.pack('<I 3f 3f', TS, *IMP_KWH, *IMP_KVARH)
v2 = struct.pack('<I 3f 3f 3f 3f', TS, *IMP_KWH, *IMP_KVARH, *EXP_KWH, *EXP_KVARH)
assert len(v1) == P.MIN_LEN_V1 == 28
assert len(v2) == P.MIN_LEN_V2 == 52

# 1.1.x record: import decoded, export absent (None, not 0.0 — "not reported"
# and "exported nothing" are different facts).
ts, kwh, kvarh, kwh_e, kvarh_e = P.decode_min(v1)
assert ts == TS and kwh_e is None and kvarh_e is None
assert all(abs(a - b) < 1e-3 for a, b in zip(kwh, IMP_KWH))
assert all(abs(a - b) < 1e-3 for a, b in zip(kvarh, IMP_KVARH))

# 1.2.0 record: all four arrays decoded.
ts, kwh, kvarh, kwh_e, kvarh_e = P.decode_min(v2)
assert ts == TS
assert all(abs(a - b) < 1e-3 for a, b in zip(kwh, IMP_KWH))
assert all(abs(a - b) < 1e-3 for a, b in zip(kwh_e, EXP_KWH))
assert all(abs(a - b) < 1e-3 for a, b in zip(kvarh_e, EXP_KVARH))

# THE REGRESSION THIS FILE EXISTS FOR: the 1.2.0 record's 28 B prefix is a valid
# 1.1.x record by design (spec B1), so a ">= 28" test accepts a 52 B payload,
# decodes import correctly, and silently drops export. Exact dispatch must treat
# the two as different shapes, and reject anything else outright.
assert P.decode_min(v2[:28]) is not None, "a real 28 B record must still decode"
for bad in (v2[:40], v2 + b"\x00", v1[:27], b"", v1 + b"\x00" * 4):
    assert P.decode_min(bad) is None, f"len {len(bad)} must be rejected, not guessed"

# ts == 0 means the clock was never set: not a valid record, at any length.
assert P.decode_min(struct.pack('<I 3f 3f', 0, *IMP_KWH, *IMP_KVARH)) is None

# sec is exact-length too.
sec = struct.pack('<I 3f 3f 3f 3f 3i 3f', TS, *(1.0,)*3, *(2.0,)*3, *(3.0,)*3,
                  *(50.0,)*3, *(4,)*3, *(0.9,)*3)
assert len(sec) == P.SEC_LEN == 76
assert P.decode_sec(sec) is not None
for bad in (sec[:75], sec + b"\x00", b""):
    assert P.decode_sec(bad) is None, f"sec len {len(bad)} must be rejected"

print("OK — exact-length dispatch: 28/52 min, 76 sec; everything else rejected")

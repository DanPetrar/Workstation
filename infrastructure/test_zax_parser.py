#!/usr/bin/env python3
"""decode_min check for zax_parser (fw 1.3.x uint32 Wh). Run: python3 infrastructure/test_zax_parser.py
Stubs paho/influxdb_client like test_zaxmodbus_parser.py: no broker, no database."""
import os, struct, sys, types

for name in ("paho", "paho.mqtt", "paho.mqtt.client",
             "influxdb_client", "influxdb_client.client",
             "influxdb_client.client.write_api"):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules["influxdb_client"].InfluxDBClient = lambda **k: types.SimpleNamespace(
    write_api=lambda **kk: types.SimpleNamespace(write=lambda **kkk: None))
sys.modules["influxdb_client.client.write_api"].SYNCHRONOUS = object()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zax_parser as P

TS = 1_767_225_600
wh = [20_000_001, 1, 0, 4_294_967_295, 2, 3, 4, 5, 6, 7, 8, 9]
d = P.decode_min(struct.pack('<I 12I', TS, *wh))
assert d[0] == TS
assert d[1] == [20000.001, 0.001, 0.0] and d[2][0] == 4294967.295 and d[4] == [0.007, 0.008, 0.009], d
d1 = P.decode_min(struct.pack('<I 3f 3f', TS, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5))   # 1.1.x, 28 B unchanged
assert d1[1] == (1.5, 2.5, 3.5) and d1[3] is None, d1
assert P.decode_min(struct.pack('<I 12I', 5, *wh)) is None                     # ts floor still applies
print("PASS zax_parser decode_min")

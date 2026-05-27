# I-003 — Python MQTT→InfluxDB Parser

_Completed: 2026-05-27_

## Service status

```
● zax-parser.service - ZaxEnergy MQTT→InfluxDB Parser
     Loaded: loaded (/etc/systemd/system/zax-parser.service; enabled; preset: enabled)
     Active: active (running) since Wed 2026-05-27 13:12:09 EEST
   Main PID: 8685 (python3)
     Memory: 32.2M

May 27 13:12:09 MainDevbox zax-parser[8685]: [PARSER] Connecting to 192.168.110.225:1883 ...
May 27 13:12:09 MainDevbox zax-parser[8685]: [MQTT] Connected (rc=Success)
May 27 13:12:09 MainDevbox zax-parser[8685]: [MQTT] Subscribed to zax_E47730/#
May 27 13:12:09 MainDevbox zax-parser[8685]: [MQTT] Subscribed to zax_73DA28/#
```

## Data arriving in InfluxDB

Data confirmed arriving for both units (Unit_A and Unit_C), all phases (R/S/T), all fields.

Sample query output (`power` measurement, last 5 minutes):

```
_measurement  unit    phase  _field  _time                          _value
power         Unit_A  R      v       2026-05-27T10:08:56.000000000Z  239.60
power         Unit_A  R      hz      2026-05-27T10:08:56.000000000Z  50.01
power         Unit_A  S      v       2026-05-27T10:08:56.000000000Z  240.00
power         Unit_C  R      v       2026-05-27T10:08:56.000000000Z  240.40
power         Unit_C  S      hz      2026-05-27T10:08:56.000000000Z  50.03
power         Unit_C  T      v       2026-05-27T10:08:56.000000000Z  239.80
```

Both units live and publishing at 1 Hz (sec topic).

## Notes

- Python dependencies (`paho-mqtt`, `influxdb-client`) were already installed in the existing venv at `/workspace/projects/mixed/ZaxEnergySurvey/collector/.venv`. The service uses that venv's Python directly rather than installing system-wide.
- Existing `zax-bridge` and `zax-influx` services were left untouched — they handle different topics (`zax/json/#`) for a separate pipeline.
- Script installed at `/opt/zax-parser/zax_parser.py` with the real token.
- Service enabled and auto-starts on boot.

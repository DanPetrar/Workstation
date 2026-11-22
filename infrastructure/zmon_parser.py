#!/usr/bin/env python3
"""zmon-parser: MQTT -> InfluxDB for ZAX-ESP-Multisensor (spec §9, plan row 10).

Subscribes '+/+' on the broker, keeps topics 'ZMON-XXXXXX/<sensor>' with a plain-number payload, writes
zmon,unit=ZMON-XXXXXX,sensor=<name> value=<float> <arrival time ns> into bucket 'zmon'.
Everything else (other projects' topics, 'status', retained or non-numeric payloads) is dropped and counted.
--dry prints the line protocol instead of writing (no influxdb_client needed).
"""
import argparse, collections, os, re, signal, sys, threading, time

UNIT = re.compile(r"ZMON-[0-9A-F]{6}")
SENSOR = re.compile(r"[A-Za-z0-9_-]{1,24}")
NUMBER = re.compile(r"-?[0-9]{1,6}(\.[0-9]{1,6})?")  # no nan, inf, exponent, no digit string that float() turns into inf: the unit sends '21.44'
RETRY_MAX = 1000                                   # points kept while a write fails; the oldest are dropped (spec §8: lost values are by design)


def parse(topic, payload, retain=False):
    """-> ('ok', unit, sensor, value) or ('drop:<reason>',)."""
    parts = topic.split("/")
    if len(parts) != 2 or not UNIT.fullmatch(parts[0]):
        return ("drop:other-topic",)
    unit, sensor = parts
    if sensor == "status":
        return ("drop:status",)
    if not SENSOR.fullmatch(sensor):
        return ("drop:bad-sensor-name",)
    if retain:
        return ("drop:retained",)                  # an old retained value would get the wrong (arrival) time
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError:
        return ("drop:not-number",)
    if not NUMBER.fullmatch(text):
        return ("drop:not-number",)
    return ("ok", unit, sensor, float(text))


def line(unit, sensor, value, ts_ns):
    return f"zmon,unit={unit},sensor={sensor} value={value!r} {ts_ns}"


class Parser:
    def __init__(self, dry, write):
        self.dry, self.write = dry, write           # write(list of lines) raises on failure
        self.lock = threading.Lock()
        self.pending = collections.deque()
        self.count = collections.Counter()

    def on_message(self, topic, payload, retain, ts_ns=None):
        r = parse(topic, payload, retain)
        with self.lock:
            self.count[r[0]] += 1
            if r[0] != "ok":
                return
            ln = line(r[1], r[2], r[3], ts_ns or time.time_ns())
            if self.dry:
                print(ln, flush=True)
                return
            self.pending.append(ln)
            while len(self.pending) > RETRY_MAX:
                self.pending.popleft()
                self.count["lost:retry-overflow"] += 1

    def flush(self):
        if self.dry:
            return
        with self.lock:
            batch = list(self.pending)
            lost0 = self.count["lost:retry-overflow"]
        if not batch:
            return
        try:
            self.write(batch)
        except Exception as e:                       # keep the batch, try again at the next flush
            with self.lock:
                self.count["write-failed"] += 1
            print(time.strftime("%T"), "write failed:", repr(e)[:160], getattr(e, "status", ""), getattr(e, "reason", ""), flush=True)
            return
        with self.lock:
            # new points were appended at the right end; points of this batch that overflowed meanwhile are already gone
            for _ in range(max(0, len(batch) - (self.count["lost:retry-overflow"] - lost0))):
                self.pending.popleft()
            self.count["written"] += len(batch)

    def summary(self):
        with self.lock:
            return " ".join(f"{k}={v}" for k, v in sorted(self.count.items())) + f" pending={len(self.pending)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--broker", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--influx", default="http://127.0.0.1:8086")
    ap.add_argument("--org", default="zax")
    ap.add_argument("--bucket", default="zmon")
    ap.add_argument("--dry", action="store_true", help="print line protocol, write nothing")
    ap.add_argument("--seconds", type=int, default=0, help="stop after N s (0 = run until killed)")
    a = ap.parse_args()

    write = None
    if not a.dry:
        token = os.environ.get("ZMON_INFLUX_TOKEN")
        if not token:
            sys.exit("ZMON_INFLUX_TOKEN not set")
        from influxdb_client import InfluxDBClient, WritePrecision
        from influxdb_client.client.write_api import SYNCHRONOUS
        api = InfluxDBClient(url=a.influx, token=token, org=a.org, timeout=5000).write_api(write_options=SYNCHRONOUS)
        write = lambda lines: api.write(bucket=a.bucket, org=a.org, record=lines, write_precision=WritePrecision.NS)

    import paho.mqtt.client as mqtt
    p = Parser(a.dry, write)
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"zmon-parser{'-dry' if a.dry else ''}-{os.getpid()}")  # a second instance must not kick the first
    c.reconnect_delay_set(1, 5)                      # T5/T6: back within 10 s of the broker, with margin for the connect time
    c.on_connect = lambda cl, ud, fl, rc, pr=None: (cl.subscribe("+/+", 0), print(time.strftime("%T"), "connected, subscribed +/+ rc", rc, flush=True))
    c.on_disconnect = lambda cl, ud, fl, rc, pr=None: print(time.strftime("%T"), "disconnected rc", rc, flush=True)
    def on_message(cl, ud, m):
        try:
            p.on_message(m.topic, m.payload, m.retain)
        except Exception as e:                       # an exception here would end paho's thread silently
            with p.lock:
                p.count["callback-error"] += 1
            print(time.strftime("%T"), "callback error:", repr(e)[:160], flush=True)
    c.on_message = on_message
    stop = []
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.append(1))  # systemctl stop: flush the queue, then exit
    c.connect_async(a.broker, a.port, keepalive=30)
    c.loop_start()
    t0 = last = lastflush = time.monotonic()        # monotonic: a stepped clock must not stop the flush (timestamps still use time_ns)
    while not stop and (not a.seconds or time.monotonic() - t0 < a.seconds):
        time.sleep(0.5)
        if time.monotonic() - lastflush >= 5:
            lastflush = time.monotonic()
            p.flush()
        if time.monotonic() - last >= 60:
            last = time.monotonic()
            print(time.strftime("%T"), "counts:", p.summary(), flush=True)
    p.flush()
    c.loop_stop()
    print(time.strftime("%T"), "final counts:", p.summary(), flush=True)


if __name__ == "__main__":
    main()

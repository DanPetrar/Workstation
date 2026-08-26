#!/usr/bin/env python3
"""Flat-file archiver for ZaxModbus units' on-device error logs.

The device's /api/errors is a rotating file (capped at ~8% of its LittleFS
partition, e.g. ~10 KB on a 128 KB S3-Zero) that drops the oldest half once
full. Hourly cron: fetch it, find where it overlaps the tail of what's
already saved here, append only the new lines. Unbounded local retention —
lets a longer interval be analysed than the device itself can hold.

If the last saved line can't be found in the new fetch (device rebooted and
rotated past our last checkpoint since the previous poll), the boundary is
unknown — a marker line is written and everything fetched is appended,
rather than silently dropping the gap or guessing.
"""
import datetime
import os
import urllib.request

UNITS = {
    "Unit_B": "192.168.20.232",
}

OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "errorlogs")
TIMEOUT = 8
EMPTY_MARKERS = ("(empty)", "(cannot open)")


def fetch(ip):
    req = urllib.request.Request(f"http://{ip}/api/errors")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode(errors="replace")


def append_new(path, fetched):
    fetched_lines = fetched.splitlines()
    if not fetched_lines or fetched.strip() in EMPTY_MARKERS:
        return 0

    if not os.path.exists(path):
        with open(path, "w") as f:
            for line in fetched_lines:
                f.write(line + "\n")
        return len(fetched_lines)

    with open(path) as f:
        existing_lines = f.read().splitlines()

    if existing_lines:
        last_known = existing_lines[-1]
        if last_known in fetched_lines:
            idx = len(fetched_lines) - 1 - fetched_lines[::-1].index(last_known)
            new_lines = fetched_lines[idx + 1:]
        else:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_lines = [f"{ts} [WATCHER] --- gap: device log rotated past "
                         f"last checkpoint, boundary unknown ---"] + fetched_lines
    else:
        new_lines = fetched_lines

    if not new_lines:
        return 0
    with open(path, "a") as f:
        for line in new_lines:
            f.write(line + "\n")
    return len(new_lines)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    for name, ip in UNITS.items():
        path = os.path.join(OUTDIR, f"{name}.log")
        try:
            fetched = fetch(ip)
        except Exception as e:
            print(f"{name}: fetch failed: {e}")
            continue
        n = append_new(path, fetched)
        print(f"{name}: +{n} new line(s)")


if __name__ == "__main__":
    main()

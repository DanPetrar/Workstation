# Workstation — Errors History

_Append one entry per non-trivial debugging session._

<!-- Format:
## YYYY-MM-DD — Short title
**Symptom:** ...
**Root cause:** ...
**Fix:** ...
-->

## 2026-07-27 — Grafana "query returned too many data points, result is truncated"

**Symptom:** on the `ZaxEnergy — Power` dashboard (`zax-power`), selecting a time range
larger than ~3h made panel data render as incomplete, and Grafana surfaced its own warning:
"A query returned too many data points and the result is truncated." Not the first time this
class of error has shown up on these dashboards.

**Root cause — confirmed regression, not a new bug:** this exact class of error was already
fixed once, on 2026-06-24 (`ZaxModbus` commit `9e8ef4c`, "downsample per-second panels via
aggregateWindow") — every raw power panel got `aggregateWindow(every: v.windowPeriod,
fn: mean, createEmpty: false)` appended specifically to prevent Grafana's row-limit
truncation on wide ranges. On 2026-07-24, a same-day dashboard edit (adding the "Open data
gaps" panel) POSTed a full dashboard JSON built from a source that predated that fix and
replaced the *entire* live panel list with `overwrite: true` — which silently: (a) dropped 3
panels (`Active Energy per minute (kWh)`, `Active Energy (kWh)`, `Board Restart Events`), and
(b) reverted all 6 power panels back to raw, un-aggregated queries. `power` is written once
per second per phase (see `zax_parser.py`), so a 3h+ window alone returns 10,000+ raw rows per
series once the `aggregateWindow` clause is gone — Grafana's InfluxDB datasource truncates the
response past its row limit instead of erroring outright, which is what read as "incomplete
data" to the user today. The panel-loss and the truncation are two symptoms of the same single
overwrite, not two separate bugs — worth stating plainly since they were diagnosed and fixed
as if separate in the first pass on 2026-07-27.

**Fix:** added `aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)` to all
6 raw power panels on `zax-power` (v14→v15), scaling resolution to the selected range instead
of shipping raw 1Hz data. Verified: 6h window went from 21,152 raw points to 2,160 aggregated
for a single series.

Audited every other dashboard on this Grafana instance for the same pattern
(`range(start: v.timeRangeStart, ...)` with no `aggregateWindow` and no small-output reducer
like `last()`/`sum()`/`count()`):
- `zax-energy` (`Active Energy (kWh)`, `Reactive Energy (kVArh)`) — same bug class, no
  `aggregateWindow`, no unit filter (pulls all units mixed). Fixed with
  `aggregateWindow(fn: last)` — safe here since these are raw cumulative-register line
  charts, not derived values.
- `bench-calib` (`SDM630 reference (live)`), `zaxmodbus-fleet` (`Total active power (W)`) —
  flagged by the "no aggregateWindow" heuristic but both end in `last()`/`sum()` reducers, so
  the response is already tiny regardless of range. Verified safe, no change.
- `bench-sec`, `zaxmodbus-board`, `zaxmodbus-dq` — already use `aggregateWindow` throughout.
  No change needed.
- `zax-power`'s `Active Energy per minute (kWh)`, `Active Energy (kWh)` (stat), and
  `Board Restart Events` — **known remaining risk, not fixed**. These compute
  `difference(nonNegative: true)` over raw per-minute energy points; `aggregateWindow` before
  a `difference()` would silently corrupt the per-interval delta math (averaging/lasting the
  cumulative register before differencing changes the answer). At today's per-minute,
  single-unit, 3-phase cardinality this only becomes truncation-prone at multi-day+ ranges,
  well past normal dashboard usage — documented here rather than patched, since a correct fix
  means restructuring the delta calc (bucket into `aggregateWindow(fn: sum)` chunks first),
  not a drop-in one-liner. Revisit if truncation is ever actually observed on these panels.

**Lesson:**
- Any Flux panel query bound to `v.timeRangeStart`/`v.timeRangeStop` against a measurement
  with sub-minute write cadence needs `aggregateWindow(every: v.windowPeriod, ...)` unless it
  already ends in a reducer that collapses the result to O(1) rows. Check new panels against
  this before shipping, not after a user hits the range that trips it.
- Never POST a dashboard update built from a reconstructed/hand-written panel list. `GET` the
  live dashboard JSON first, edit that object in place (append/modify only the panels you
  intend to touch), and POST the result back — anything else risks silently reverting fixes
  that only exist in the live dashboard and not in whatever source you started from. The two
  repo-tracked exports (`infrastructure/grafana-power-dashboard.json` here,
  `Doc/grafana/zax-power.json` in ZaxModbus) are stale-prone documentation snapshots, not
  redeploy sources — they were also both found out of date during this incident.

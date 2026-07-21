# Workstation → Workspace — Purpose Reformulation

Base doc for the reformulation; becomes the spec once settled.

## Status: implementation complete (2026-07-21)

`DanPetrar/Workspace` exists, structure built per the "Structure — Revision for
Flexibility" section below, pushed (`c22dbbe`, then `6773563` for the Futro plan).
`raspi` and `workstation` nodes are `active` and live-verified; `futro` is `planned`
with a full setup plan written (`nodes/futro/setup-plan.md`). The old `Workstation`
repo (this one) is untouched, per the "safe until cutover" decision. See the updated
**Decisions** section below for what's resolved vs. still open.

## Why

Current README frames this repo as "Android dev machine coordinated from the Pi." Reality:
it already hosts the permanent InfluxDB/Grafana/Mosquitto stack + parsers for every
project. The reformulation brings the repo in line with what it actually is (and is
about to become).

## Directions so far

1. **Rename Workstation → Workspace**, built as a **new, separate project** — the live
   Workstation repo stays untouched until Workspace is complete and validated, then
   cutover happens (rename/replace/archive).

2. **Scope broadens to all dev hardware, not one machine.** Nodes:
   - RaspPI (Pi 4, 1 GB RAM, 32 GB SD) — this Pi
   - Workstation (i3, 8 GB RAM, 2×240 GB SSD) — folded in as one node
   - Fujitsu Futro S740 (Celeron, 8 GB DDR4, 500 GB SSD) — planned, not yet acquired

3. **Role split once the Futro exists:** Futro = "RaspPI clone," inherits the Pi's
   current role with far more headroom. Pi narrows to **testing station** (physical
   hardware-attached work — serial/USB/GPIO/RS-485 bench wiring — tied to its physical
   cabling). *Open: exactly what "clone" transfers, incl. whether Claude Code
   coordination itself moves — decide once the Futro is in hand.*

4. **New doc structure:**
   - `infrastructure-hardware.md` — components/config/setup/role, per node
   - `infrastructure-interaction.md` — multi-node data-flow map (successor to
     `INFRASTRUCTURE.md`, which today only covers Pi↔Workstation)
   - One operational log per node (installed software, upgrades, running tasks)
   - A test-units file (Unit_A–D + future) — *overlaps ZaxModbus's own
     `boards.json`/`units.yaml`; resolve duplication vs. cross-reference at
     implementation time*

5. **Futro bring-up:** minimal human steps (OS install, network, SSH key) → Claude (on
   the Pi, via SSH) completes the rest. Same pattern already proven with Workstation.

6. **OS: Debian 13 (trixie) x86_64** — matches the Pi's actual OS exactly (checked live).
   *Correction found: Workstation's README claims "Debian," it's actually Ubuntu 26.04
   live — stale doc, unrelated to this decision but worth fixing separately.*
   **Deliverable:** step-by-step human install doc, ending at SSH reachability.

## Decisions

- **Timing:** ✅ done — built now, per the original decision. Futro is a placeholder
  entry (`nodes/futro/`, status `planned`) until the hardware exists.
- **Cutover criteria (refined by Fable's structure, see below):** per-node, not global
  — an `active` node's docs must be live-verified; a `planned` node only needs a
  correctly-labeled placeholder. **`raspi` and `workstation` both meet this today.**
  Cutover (retiring this repo) is **not yet decided/performed** — meeting the criteria
  doesn't auto-trigger it; that's a separate, still-open call.
- **Coordinator role (Pi vs. Futro): ✅ RESOLVED (2026-07-21).** The Futro takes over
  the coordinator role **in full** — every task currently run by the Pi's Claude Code
  session — once bring-up completes. `raspi` narrows to testing-station only
  (physically-tied hardware work: USB/serial/GPIO/RS-485/flash — pinned to its
  cabling, doesn't transfer). Recorded in `nodes/INDEX.md`'s `role` fields and fully
  planned in `nodes/futro/setup-plan.md` (Linux version, partitions, human install
  steps, Pi-Claude-driven remote completion, 9-point validation). `raspi` remains the
  practical coordinator until the Futro exists and all 9 validation checks pass.

## Structure — Revision for Flexibility

Same substance as "Directions so far," restructured so neither a 4th node nor the
coordinator-role decision requires editing prose scattered across multiple files.
**Principle:** node count and role assignments live in exactly one data table; every
other doc references that table instead of restating it.

### Layout

```
Workspace/
  README.md                     — what this repo is, scope statement, links to INDEX.md
  COORDINATION.md                — session-handoff workflow; roles pulled from nodes/INDEX.md
  infrastructure-interaction.md  — multi-node data-flow map + operating rules (fleet-wide policy)
  infrastructure/                — health scripts, deploy notes, dashboard JSON (one per node, ported as-is)
  test-units.md                  — bench unit docs (role/wiring/purpose only — see authority note below)
  nodes/
    INDEX.md                     — table: node, role, status (active|planned), IP, link
    raspi/
      hardware.md
      status.md
      inventory.md
      setup/
    workstation/
      hardware.md
      status.md
      inventory.md
      setup/
    futro/
      hardware.md                — placeholder while status=planned
```

Adding a node = adding a `nodes/<name>/` directory and a row in `INDEX.md`. No other
file needs to change just because the node count changed.

### Resolving the three flagged issues

**#1 — cutover criterion vs. "start now."** Redefine "verified accurate" per node,
not globally. A node's status is `active` or `planned`. Cutover requires: (a) every
`active` node's `hardware.md`/`status.md`/`inventory.md` verified against live state,
and (b) `infrastructure-interaction.md` + `test-units.md` verified against live state.
A `planned` node (Futro, today) only needs a correctly labeled placeholder in
`INDEX.md` + a stub `hardware.md` — its "accuracy" bar is "correctly marked as not yet
acquired," which is trivially met now. This makes cutover reachable with Pi +
Workstation alone; Futro going `planned → active` is a later, separate event (the
bring-up workflow) that doesn't reopen or block cutover.

**#2 — per-node log vs. STATUS.md/inventory.md/setup/.** Not a new fourth thing —
these three existing mechanisms *become* the per-node log, split by node instead of
collapsed into one global file. `nodes/<node>/status.md` succeeds the relevant slice
of today's `STATUS.md`, `nodes/<node>/inventory.md` succeeds today's `inventory.md`,
`nodes/<node>/setup/` succeeds today's `setup/`. No duplicate concept is introduced.

**#3 — boards.json authority.** Decided: `/home/pi/boards.json` (read live by
`flash_guard.py` before every flash) is the sole authority for board identity,
firmware, version, and last-flash time. `test-units.md` is documentation-only — bench
role, physical/wiring location, purpose — keyed by MAC to cross-reference
`boards.json` entries, and must **never** carry firmware/version/last-flash fields.
State this as a header warning in `test-units.md` itself.

### How #4–#8 are accommodated

- **#4 (COORDINATION.md tied to open coordinator question):** role is a field in
  `nodes/INDEX.md`, not prose. When the question resolves, flip the field + update one
  SSH-target detail in `COORDINATION.md` — no restructuring.
- **#5 ("clone" broader than the Claude Code question):** the physically-pinned
  responsibilities (USB/serial/RS-485, firmware flash) are a property of the node
  itself (documented in that node's `hardware.md`, tied to its cabling), separate from
  the "coordinator" role field. The two axes move independently instead of being
  bundled into one "clone" concept.
- **#6 (rename/replace/archive ambiguity):** sidestepped by construction — Workspace
  is built as a fully independent repo now, so nothing in the initial build depends on
  which cutover mechanism is eventually used. That choice is deferred to cutover time,
  out of scope for this build.
- **#7 (no scope boundary):** `README.md` states a one-line rule — infra/hardware/
  coordination lives here; project-specific specs/firmware/test-plans stay in project
  repos. `test-units.md` states its own scope (bench role only, not firmware data).
- **#8 (OS divergence, credentials):** OS/package-manager differences are naturally
  isolated per node since `hardware.md` is per-node already — no fleet-wide doc has to
  reconcile Debian vs. Ubuntu. Credential handling is carried over unchanged from
  today's `STATUS.md` pattern (plaintext, in-repo); flagged here as an existing risk
  being scaled to more nodes, not a new one — not addressed further by this structure.

## Implementation Plan (for a Sonnet-model executing agent)

Read this whole plan before starting. Do not invent specs, service lists, or config
values not confirmed by a live check — every step marked **VERIFY** means SSH/read the
real system, not paraphrase this file or `INFRASTRUCTURE.md`/`STATUS.md`, which may
already be stale. Where this file's own directions (e.g. Futro's CPU/RAM/disk) haven't
been independently confirmed, carry them over labeled "as stated, unverified" rather
than presenting them as checked.

**Do not touch the existing `Workstation` repo or its remote.** Build entirely in a
new local directory and new GitHub repo. Do not perform any cutover action (no
renaming/archiving `Workstation`) — that is a future, separate decision.

1. **Create the repo.**
   - `mkdir -p ~/Workspace && cd ~/Workspace && git init`
   - `gh repo create DanPetrar/Workspace --public --source=. --remote=origin`
     (match the existing `Workstation` repo's visibility: PUBLIC)

2. **Scaffold the empty structure** exactly as laid out above (directories +
   files with headings only, no content yet): `README.md`, `COORDINATION.md`,
   `infrastructure-interaction.md`, `test-units.md`, `infrastructure/`,
   `nodes/INDEX.md`, `nodes/raspi/{hardware,status,inventory}.md` +
   `nodes/raspi/setup/`, `nodes/workstation/{hardware,status,inventory}.md` +
   `nodes/workstation/setup/`, `nodes/futro/hardware.md`.

3. **`nodes/INDEX.md`** — one table: `node | role | status | IP | notes/link`.
   Fill in raspi and workstation now (**VERIFY** IPs against live `ip addr`/`ssh ws`,
   don't just copy from `INFRASTRUCTURE.md`). Futro row: role/status = `planned`,
   IP = blank, note "not yet acquired."

4. **`nodes/raspi/hardware.md` — VERIFY locally.** Run on the Pi directly:
   `uname -a`, `cat /etc/os-release`, `nproc`, `free -h`, `df -h`, `lsblk`. Do not
   reuse the "Pi 4, 1 GB RAM, 32 GB SD" line from this file without confirming it —
   check actual model (`cat /proc/device-tree/model` or similar) and SD size.

5. **`nodes/workstation/hardware.md` — VERIFY via `ssh ws`.** Same checks as step 4,
   run over SSH. `STATUS.md`/`INFRASTRUCTURE.md` already record OS as Ubuntu 26.04
   (README.md says Debian — known-stale, per this file's direction 6); confirm live
   and record the corrected value here, since this doc absorbs that fix rather than
   deferring it further.

6. **`nodes/futro/hardware.md` — placeholder only.** Carry over CPU/RAM/disk from
   this file's direction 2, explicitly labeled "as stated by user, unverified —
   hardware not yet acquired." Do not add anything not already in this planning doc.
   Status stays `planned` until a future bring-up session flips it.

7. **`nodes/raspi/status.md`, `inventory.md`** and **`nodes/workstation/status.md`,
   `inventory.md`** — seed by splitting the existing global `STATUS.md` and
   `inventory.md` (in the old `Workstation` repo, read-only reference) into the
   entries that belong to each node. **VERIFY** current running services/tasks per
   node rather than trusting the old files' dates are still current (e.g. re-check
   `systemctl` state on both machines). `setup/` directories: copy the existing
   per-session setup files over, splitting by which machine each session was on.

8. **`infrastructure-interaction.md`** — migrate sections 2 ("Data-flow / broker
   map") and 3 ("Operating rules") of the old repo's `INFRASTRUCTURE.md`.
   **VERIFY**, don't copy verbatim: re-check which services are actually running
   (`ssh ws systemctl list-units`), which brokers have which subscribers, before
   writing the map. Note explicitly that this file also owns the "where does new work
   go" operating rules — this is fleet-wide policy, not a per-node fact.

9. **`infrastructure/`** — port `health-pi.sh`, `health-ws.sh`, and the tracked
   Grafana dashboard JSON files from the old repo's `infrastructure/` directory as-is
   (working scripts, no rewrite needed). Add stub `health-futro.sh` only when Futro
   goes active, not now.

10. **`test-units.md`** — read `/home/pi/boards.json` directly. For each unit
    currently on the bench (Unit_A–D + any others present), record: name, MAC (as the
    cross-reference key), bench role/physical location, purpose. Do **not** copy
    `firmware`, `version`, or `last_flash` fields — state at the top of the file, in
    these words or close to them: "`boards.json` on the Pi is the sole authority for
    board identity/firmware/version; this file never duplicates those fields."

11. **`COORDINATION.md`** — write the session-handoff workflow (adapt from the old
    repo's `COORDINATION.md`), but phrase role assignment as "coordinator = the node
    marked `role: coordinator` in `nodes/INDEX.md`" rather than hardcoding "Pi." Today
    that resolves to raspi — state today's resolution plainly, but through the
    indirection, not as a hardcoded fact restated in multiple places.

12. **`README.md`** — short: what Workspace is, the one-line in/out scope rule from
    the Structure section above, links to `nodes/INDEX.md` and
    `infrastructure-interaction.md`.

13. **Commit and push** to `DanPetrar/Workspace`. Do not modify, rename, or archive
    `DanPetrar/Workstation`.

14. **Report back**, explicitly listing: which fields were VERIFIED live vs. carried
    over labeled unverified (Futro only), and any discrepancy found between this
    planning doc / the old repo's docs and live system state (e.g., if the Pi's RAM or
    Workstation's OS turns out to differ from what's written anywhere above).

## External review (Fable, before implementation)

1. **Cutover criterion contradicts the timing decision.** "Verified accurate against
   live state" can't be satisfied by the Futro's placeholder docs — so cutover still
   silently waits on the Futro despite "start now" being chosen to avoid that. Needs an
   explicit call: does a correctly-marked placeholder count as "accurate," or does
   cutover proceed with 2 of 3 nodes fully live?
2. **Per-node operational log overlaps `STATUS.md`/`inventory.md`/`setup/`** (all
   actively maintained today) — a bigger unflagged overlap than the boards.json one.
   Needs the same "fold in / keep alongside / retire" decision.
3. **boards.json isn't just a doc — `flash_guard.py` reads it live** before every flash
   to prevent bricking. Whatever resolves the test-units-file overlap must make clear
   which copy is authoritative for flash decisions, not just avoid literal duplication.
4. `COORDINATION.md` likely gets written twice — once now (Futro as 3rd executor under
   the current 2-node pattern), again once the coordinator-role question resolves.
5. "Futro = RaspPI clone" is narrower than reality — some of the Pi's role (physical
   hardware attachment: serial/GPIO/RS-485) can't transfer at all, only the Claude Code
   piece is flagged as open.
6. Rename mechanics ("rename/replace/archive") aren't committed to one — they have
   different blast radius for anything referencing the repo by name/path.
7. No stated scope boundary for Workspace — risk of scope creep (e.g. pulling
   firmware/task-spec history in) given the units-file line is already blurry.
8. Deferred README OS-correction (Debian claimed, Ubuntu actual) has no owner/tracking.

**Verdict:** direction is sound, "safe until cutover" strategy is good. #1 and #2 are
the two worth resolving before implementation starts.

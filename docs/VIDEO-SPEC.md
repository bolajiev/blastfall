# Blastfall — Demo Video Spec (Hack Hydra submission)

## Constraints (hard)

- **Max 3:00.** Anything past gets unreviewed — cut hard.
- **Real product footage only.** No stock motion graphics, no AI-slop title
  cards, no zoom-whoosh transitions.
- **Screen capture:** 60fps min, 1440p+, cursor visible and deliberate (script
  the path, no jitter).
- **Terminal segments:** record with `scripts/video/capture_terminal.py` (ttyd +
  Playwright, deterministic typing, no typos/backspaces on camera).
- **Browser/UI segments:** Kap or native OS recorder, 1440p, cursor highlight
  ON, no webcam bubble.
- **Edit:** ffmpeg / DaVinci Resolve. Hard cuts or 200ms crossfades only.
- **No AI voiceover** unless it's clearly you, scripting real words. No
  countdown/hype intro. No music that fights the terminal audio. No
  "thank you for watching" card — end on the last query result.

## The one motion rule

The graph reveal (below) is the only place animation earns its keep: the
compromised node pops in red, then your services in green, then the exposed
versions **stream in** as the traversal returns them (force-directed). Everywhere
else: static, let the data be read (each result holds ≥2s).

## Script structure (timestamps are hard caps)

### 0:00–0:20 — Cold open
On-screen text, no narrator preamble, no logo:
> **TanStack, May 2026 — 84 malicious artifacts across 42 packages in 6 minutes.**
> The defender's question: compromised at 09:00, which of my services are
> exposed by 09:06?

### 0:20–0:45 — What you built (one sentence, over terminal booting)
"Blastfall ingests the real npm dependency graph into HydraDB — every version,
publish date, and maintainer — and answers the blast radius as a graph
traversal, not a similarity search."

### 0:45–1:10 — Terminal segment (capture_terminal.py, deterministic)
`./bin/blastfall scan ms@2.1.3` — capture_terminal.py types the query and the
summary prints. Hold ≥3s on:
```
[compromised] ms@2.1.3
exposed versions : 1751
exposed packages : 56
services exposed : auth-service, payments-api, reports-worker, search-api
direct dependents: 409
```

### 1:10–1:30 — Graph reveal (the one motion shot)
UI, compromise `ms@2.1.3`, hops 6. Red node first, then green services, then
blue versions stream in. "Here's the reverse-dependency closure — 1,751 versions
found by walking *incoming* DEPENDS_ON edges."

### 1:30–1:50 — Temporal: which version introduced it + resolution window
UI, two panels, read one row each:
- "Which version introduced it": `debug` first pulled in `ms@2.1.3` at
  `debug@4.3.7` (Sep 2024) — anything ≥ carries it.
- Set attack time, re-compromise: the resolution window lists releases that
  shipped the bad version between publish and discovery.

### 1:50–2:15 — Shared maintainers + typosquats
UI: maintainer `jasonsaayman` → axios, etc.; `ms`'s close-name neighbors
(`fs`, `is`, `mv`, `mz`, `qs`, `ws`).

### 2:15–2:45 — The paragraph that matters (over the running MSpaths query)
UI worm panel: `rc, colors`, hops 5, Union blast radius. Say:
> "This is a reverse closure over millions of versioned nodes — a vector index
> can't do this at all. Two real hijacked packages cover 2,000 exposed versions
> and 82 packages in one batched `algo.MSpaths` call, resolved server-side
> through the property index."

### 2:45–3:00 — HydraDB callout (end on the last query result)
"Blast radius is `algo.MSpaths`/`SSpaths` traversal on object-storage-backed
versioned graph — sub-second at six hops. This needed a real graph database,
not a vector index bolt-on." End on the worm result on screen.

## Capture files

### Terminal — `scripts/video/capture_terminal.py` (drives `bin/blastfall`)
Deterministic recording of the terminal segment on a real browser-rendered
terminal (ttyd + Playwright), 1440×810, no typos: the script types the real CLI
commands and holds on the output. Requires `ttyd` running (`ttyd -p 7777 -W -w
<repo> ...`) and the app up. The commands run on camera are the real product
CLI: `./bin/blastfall scan ms@2.1.3` and `./bin/blastfall scan rc@1.2.8`.

### Browser — click path (script it; no jitter)
1. Featured chip **`ms@2.1.3`** → Compromise (hops 6). Cards + graph reveal.
2. "Which version introduced it" panel.
3. Set attack time today, re-Compromise → Resolution window.
4. Scroll: Shared maintainers, Typosquats.
5. Worm panel: `rc, colors` → Union blast radius (hops 5).
Cursor: move in straight paths, land on the target, hold. Each panel ≥2s.

## Expected numbers (sanity anchors)

| Scenario | exposed versions | services |
|---|---|---|
| `ms@2.1.3`, hops 6 | ~1,751 | 4 of 5 |
| `rc@1.2.8`, hops 5 | ~419 | — |
| `colors@1.4.0`, hops 5 | ~80 | — |
| `rc, colors` union, hops 5 (MSpaths) | ~2,000 | — |

## Submission form answers (copy-paste)

- **Project name:** Blastfall
- **Short description:** Supply-chain blast radius on a versioned npm dependency
  graph built on HydraDB. Compromise a `name@version` and get the transitive
  reverse-dependency closure, which of your services are exposed, the version
  that introduced the vulnerability, the resolution window between publish and
  discovery, shared maintainers, and typosquats — all as graph traversal.
- **Problem addressed:** Defenders need transitive exposure answers in minutes,
  not per-package lookups across deps.dev/Snyk/OSV. That's a versioned graph
  traversal, which vector indexes cannot do.
- **How it uses the HydraDB OS repo:** HydraDB is the database. Exposure reports
  are `algo.SSpaths`/`algo.MSpaths` traversals over versioned `DEPENDS_ON`
  edges; windows, maintainers, and typosquats are property-filtered `MATCH`
  queries. Nothing precomputed client-side. Property indexes (built on write)
  resolve MSpaths sources server-side in one batched call.
- **Tech stack:** HydraDB (docker, object-storage-native), npm registry
  metadata, Python (FastAPI + uvicorn), OpenCypher via HydraDB HTTPS API.
- **Dataset:** npm registry package docs (public); demo org services in
  `app/services.py`. Resolution follows npm semantics.
- **GitHub repo:** https://github.com/bolajiev/blastfall
- **Video:** <your unlisted YouTube link>

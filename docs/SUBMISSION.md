# Hack Hydra 2026 — Submission Form Answers

## Project Name
Blastfall

## Project Description
Supply-chain blast radius on a versioned npm dependency graph built on HydraDB.
Simulate a compromise of any package@version and get the transitive
reverse-dependency closure, which of your services are exposed, the version
that introduced the vulnerability, the resolution window between publish and
discovery, shared maintainers, and typosquat adjacency — all as graph traversal.

## What problem are you solving?
Software supply-chain attacks are worm-driven and fast. When a package is
compromised at 09:00, defenders need to know which of their services are
transitively exposed by 09:06. That is a transitive reverse-dependency closure
over a versioned ecosystem graph — the kind of question a vector index cannot
answer at all. Existing tools answer one package at a time over slow HTTP
lookups, and none of them can overlay your own services on the dependency graph
or answer time-based questions like "which version introduced the vulnerability."

## What did you build?
Blastfall ingests the real npm dependency graph into HydraDB — package
versions, publish dates, maintainers, typosquat candidates — and answers
exposure questions as graph traversal:

- **Blast radius:** every package version transitively depending on a
  compromised `name@version`, in k hops (`algo.SSpaths` over reverse
  `DEPENDS_ON` edges).
- **Service exposure:** the demo org's services are nodes sharing the same
  edge type, so a single traversal surfaces which of *your* services are exposed.
- **Which version introduced it:** for each affected package, the first version
  that resolved to the bad release (temporal, from the version timeline).
- **Resolution window:** dependents that shipped the bad version between publish
  and discovery.
- **Shared maintainers + typosquats:** single-hop traversals (maintainer
  adjacency and edit-distance-1 name adjacency).
- **Worm scenario:** union blast radius across many compromised packages at once
  via `algo.MSpaths` — sources resolved server-side through the property index,
  no client-side query fan-out.

## How does your project use HydraDB?
HydraDB is the database — the entire project runs on it. The graph model is
versioned and temporal: `Service`, `Package`, `Version`, and `Maintainer` nodes
with resolved `DEPENDS_ON` edges (each edge is a concrete package version,
resolved npm-style at publish time), plus `HAS_VERSION`, `DECLARES`, `MAINTAINS`,
and `TYPOSQUAT` edges. Exposure reports are `algo.SSpaths`/`algo.MSpaths`
traversals over those edges; windows, maintainers, and typosquats are
property-filtered `MATCH` queries. Property indexes (built on write) resolve
MSpaths sources server-side in one batched call. Nothing is precomputed
client-side. Without HydraDB's graph storage and traversal kernels, this would
be a pile of per-package API calls and a hand-rolled closure — slower, and with
none of the time-travel.

## Tech Stack
HydraDB (docker, object-storage-native graph database), npm registry metadata,
Python, FastAPI + uvicorn, OpenCypher via HydraDB's HTTPS API, Playwright +
ffmpeg (demo capture), edge-tts (voiceover).

## Deployed Project URL
Not deployed. Runs locally in one command: `./scripts/up.sh` → `http://localhost:8123`
(demo video and repo show it working end-to-end).

## Anything else the judges should know? (optional field)

Built on real npm metadata: ~112K package versions, ~359K resolved edges from
the top ~2.5K packages plus their transitive closure. Every DEPENDS_ON edge is
a concrete version resolved npm-style at publish time, so the graph is
versioned and temporal. Honest limits: the universe is the dense core, not
all of npm; typosquats are edit-distance-1 only; resolution is publish-time,
not lockfile simulation. Reproduce everything with ./scripts/up.sh.

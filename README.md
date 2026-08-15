# Blastfall

Supply-chain blast radius on a **versioned dependency graph** built with
[HydraDB](https://github.com/hydra-db/hydradb) — the open-source graph database
on object storage.

When a package gets compromised, the defender's question is *speed*:

> A package is compromised at 09:00. Which of your services are transitively
> exposed by 09:06?

That is a **transitive reverse-dependency closure** over a versioned ecosystem
graph — the exact problem a vector index cannot answer. Blastfall ingests the
real npm dependency graph (all versions, publish dates, maintainers) into
HydraDB and answers it with HydraDB's native graph traversal:

- **Blast radius** — every package *version* transitively depending on a
  compromised `name@version`, in k hops
- **Service exposure** — which of *your* services resolve to the compromised
  version, directly or transitively
- **Worm scenario** — the union blast radius across many compromised packages at
  once via `algo.MSpaths` (sources resolved in one batched call through the
  property index, not a client-side query per package)
- **Resolution window** — which releases pulled in the bad version between when
  it was published and when the attack was discovered
- **Which version introduced it** — for each affected package, the first version
  that resolved to the compromised dependency (temporal, from the version
  timeline)
- **Shared maintainers** — other packages maintained by the same people
- **Typosquats** — close-name impostors that sit adjacent to popular packages

Try the featured incidents preset in the UI: `rc@1.2.8` (2021 ua-parser-js
hijack), `colors@1.4.0` (2022 sabotage), `event-stream@4.0.1` (2018 Copay
attack), or the multi-compromise worm panel (`rc, colors`).

## How it works

The demo org's services are `Service` nodes with `DEPENDS_ON` edges into the
resolved versions of their dependencies. Because `Service -> Version` and
`Version -> Version` share one edge type, a single reverse traversal from a
compromised version surfaces the exposed services automatically.

```
Service ─DEPENDS_ON→ Version ─DEPENDS_ON→ Version … → compromised version
```

Graph model in HydraDB:

| Label | Meaning | Key properties |
|---|---|---|
| `Package` | an npm package | name, latest |
| `Version` | `name@version` | name, version, publishedAt |
| `Maintainer` | an npm maintainer account | name |
| `Service` | one of your org's apps | name |

| Edge | Semantics |
|---|---|
| `Package -[:HAS_VERSION]-> Version` | version membership |
| `Version -[:DECLARES]-> Package` | a *declared* dependency (name + range) |
| `Version -[:DEPENDS_ON]-> Version` | a *resolved* dependency (highest version satisfying the range at publish time) |
| `Service -[:DEPENDS_ON]-> Version` | a service resolving a range to a version |
| `Maintainer -[:MAINTAINS]-> Package` | package ownership |
| `Package -[:TYPOSQUAT]-> Package` | edit-distance-1 name adjacency |

## Stack

- **HydraDB** (docker image `ghcr.io/hydra-db/hydradb:latest`) — graph storage + traversal
- **npm registry** — bulk package metadata (all versions, publish times, maintainers)
- **Python** (`fastapi` + `uvicorn`) — ingestion pipeline and demo API
- **OpenCypher** via HydraDB's Neo4j-compatible Bolt/HTTPS API

## Quickstart

Requirements: `docker`, `python3` (3.10+). ~5-15 minutes on a laptop.

```bash
git clone <this repo> && cd blastfall
./scripts/up.sh              # start HydraDB, ingest the npm universe, run the app
open http://localhost:8123
```

`scripts/up.sh` starts HydraDB in a container, ingests the versioned dependency
graph for the top ~2,500 npm packages (default; set `MAX_PACKAGES` to grow it),
ingests the demo org, and serves the app. The first run fetches metadata from
`registry.npmjs.org` and takes a few minutes; it's cached under `data/` (which
is gitignored).

Manual steps:

```bash
# 1. HydraDB (or `docker run` per the README at github.com/hydra-db/hydradb)
# 2. ingest the graph
MAX_PACKAGES=2500 python3 -m ingest.build_graph
# 3. ingest the demo org
python3 -m app.services
# 4. run the app
python3 -m uvicorn app.server:app --port 8123
```

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/packages?q=lod` | package prefix search |
| `GET /api/versions/express` | versions + publish dates |
| `GET /api/incidents` | featured real-incident presets |
| `POST /api/compromise` | simulate a compromise: `{name, version, maxLen, attackTime?}` |
| `POST /api/multi-compromise` | worm scenario: `{packages: [...], maxLen}` — union blast radius via `algo.MSpaths` |

The `POST /api/compromise` response includes the exposure report, direct
dependents, resolution window, typosquats, shared maintainers, and a sampled
subgraph for visualization. `POST /api/multi-compromise` uses HydraDB's
`algo.MSpaths` so the union traversal across all compromised packages happens
server-side in one batched call.

## Repository layout

```
ingest/            registry fetch + cache, semver resolution, graph model, HydraDB loader
  registry.py      npm registry client + package-level closure discovery
  semver_range.py  npm range matching (caret/tilde/partial/comparison sets)
  model.py         nodes/edges + version resolution + typosquat discovery
  hydradb.py       HydraDB HTTPS client + batched UNWIND loader
  build_graph.py   orchestration: fetch -> model -> ingest
app/               demo application
  graph.py         query layer (blast radius, dependents, windows, maintainers, typosquats)
  services.py      demo org manifest -> Service nodes
  server.py        FastAPI
  static/          single-page UI (graph reveal animation)
scripts/up.sh      one-shot bring-up
scripts/video/     vhs tape + demo query for the submission video
docs/VIDEO-SPEC.md 3-minute demo video spec (timeline, capture files, form answers)
```

## Data & attribution

- npm package metadata: `registry.npmjs.org` (public, MIT/X11 license terms of
  npm's public registry data).
- Dependency *resolution* follows npm semantics: a declared range resolves to
  the highest version published on or before the dependent version's publish
  date that satisfies the range.
- Typosquat edges are computed offline as edit-distance-1 name variants that
  exist in the universe; no claims are made about intent.
- Built for [Hack Hydra](https://hackhydra.hydradb.com) (Aug 12-20, 2026),
  Track 02 — "Repos, dependencies and code as graphs".

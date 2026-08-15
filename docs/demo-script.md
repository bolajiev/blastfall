# Blastfall — demo video script (≤3:00) & submission notes

## 3-minute demo script

### 0:00-0:15 — The problem
"Software supply-chain attacks are worm-driven now. In the TanStack compromise
this May, 84 malicious artifacts were published across 42 packages in six
minutes, and it propagated to hundreds of npm and PyPI packages. The defender's
question is speed: a package is compromised at 09:00 — which of my services are
transitively exposed by 09:06? That's a transitive reverse-dependency closure
over a versioned graph. A vector index cannot answer it. I built it on HydraDB."

### 0:15-0:40 — What I built
"Blastfall ingests the real npm dependency graph into HydraDB — package
versions, publish dates, maintainers. Every version resolves its declared
dependency ranges the way npm actually would. My demo org's services are nodes
in the same graph. Now compromise a package and see who's exposed — the graph
does the work."

### 0:40-1:20 — Live demo: the compromise
"Let's compromise `ms@2.1.3` — a tiny utility that half the ecosystem pulls in."
[type ms / select 2.1.3 / hit Compromise]
"1,751 package versions transitively depend on it. Four of our five services are
exposed — auth, payments, reports, search. Here's the reverse-dependency
closure — 400+ direct dependents, and the subgraph is traversed from HydraDB's
native path procedures."

### 1:20-1:50 — Resolution window
"Now the harder question: which of our own releases pulled the bad version in
before we caught it? Set the attack time and Blastfall filters dependents that
resolved to it between publish and discovery — that's the lockfile window.
Temporal versioning in HydraDB makes this a WHERE clause, not a pipeline."

### 1:50-2:15 — Typosquats + shared maintainers
"Close-name impostors sit right next to a popular package. `ms` has six
edit-distance-one neighbors in the universe. And packages that share a
maintainer are the next wave to watch — all single-hop traversals."

### 2:15-2:45 — Why HydraDB
"Blast radius at six hops returns in well under a second on this graph, because
it's a graph traversal — not a similarity search. The graph model is versioned
and temporal: every `DEPENDS_ON` edge is a resolved version, every version has a
publish time. Storage is object-backed and cheap. What would this be without
HydraDB? A pile of per-package API calls and a hand-rolled closure — slower, and
with none of the time-travel."

### 2:45-3:00 — Wrap
"Blastfall. Compromised at 09:00, exposed by 09:06. Repo, attribution, and the
full model are on GitHub."

---

## Submission form notes

- **Project name:** Blastfall
- **Description:** Supply-chain blast radius on a versioned npm dependency
  graph built on HydraDB. Compromise a package@version and get the transitive
  reverse-dependency closure, which of your services are exposed, the
  resolution window between publish and discovery, shared maintainers, and
  typosquat adjacency — all as graph traversal.
- **Problem addressed:** Defenders need transitive exposure answers in minutes,
  not per-package lookups across deps.dev/Snyk/OSV. That's a versioned graph
  traversal, which vector indexes cannot do.
- **How it uses the HydraDB OS repo:** HydraDB is the database. The whole
  exposure report is one `algo.SSpaths` reverse traversal over versioned
  `DEPENDS_ON` edges plus property-filtered `MATCH` queries for windows,
  maintainers, and typosquats. Graph-native; nothing precomputed client-side.
- **Tech stack:** HydraDB (docker), npm registry metadata, Python (FastAPI +
  uvicorn), OpenCypher via HydraDB HTTPS API.
- **Dataset:** npm registry package docs (public); demo org services defined in
  `app/services.py`. Resolution follows npm semantics.

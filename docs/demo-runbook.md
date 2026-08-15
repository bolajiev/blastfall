# Blastfall — demo runbook (for the 3-minute video)

Record in **one continuous screen session**. Use a clean browser window, ~1440p,
no bookmarks bar. Numbers below are the *expected* live outputs on the default
2,500-package universe — if yours differ slightly it's fine; the story is the
same. App: `http://localhost:8123`.

## Take 1 (0:00-0:40) — The problem + what you built
Open narration over the **worm scenario** panel:
"Software supply-chain attacks are worm-driven now. TanStack's CI was breached
in May and 84 malicious artifacts went out across 42 packages in six minutes.
The defender's question is speed: compromised at 09:00, which of my services
are exposed by 09:06? That's a transitive reverse-dependency closure over a
versioned graph — a vector index cannot answer it. Blastfall ingests the real
npm dependency graph into HydraDB and answers it as traversal."
Mouse over the model: every `DEPENDS_ON` edge is a *resolved version*, every
version has a publish date; the demo org's services are nodes in the same graph.

## Take 2 (0:40-1:40) — Live compromise
1. Click the featured-incident chip **`ms@2.1.3`** (or type `ms`, select 2.1.3,
   hops 6).
2. Click **Compromise**.
3. Read the cards, top to bottom:
   - **1,751 exposed versions, 56 packages, 4 of 5 services exposed.**
   - Exposure map: red node is the compromise; blue = exposed versions,
     green = your services (auth-service, payments-api, reports-worker,
     search-api).
   - "web-dashboard survives because it never resolves `ms`."
4. Say: "Four services pull it in transitively, and HydraDB found them by
   walking *incoming* `DEPENDS_ON` edges — one traversal, ~150ms."

## Take 3 (1:40-2:10) — Which version introduced it
1. Scroll to **"Which version introduced it"**.
2. Read: "A defender's second question: *which version of the dependency
   introduced the vulnerability?* For each affected package, Blastfall finds the
   first version that resolved to the bad release — `debug` first pulled in
   `ms@2.1.3` at `debug@4.3.7` in September 2024. Anything on `debug >= 4.3.7`
   carries it. That's a WHERE clause over HydraDB's versioned, temporal graph,
   not a pipeline."

## Take 4 (2:10-2:45) — Resolution window + worm scenario
1. Set **attack time** to today (e.g. `08/14/2026 09:00 AM`), re-Compromise.
   Scroll to **Resolution window** — dependents released between when the bad
   version went live and when you caught it. "These are the releases that could
   have shipped the compromised code before you knew."
2. Go up to the **Worm scenario** panel: type `rc, colors`, hops 5, click
   **Union blast radius**.
3. Read: "`rc` and `colors` — two real hijacked packages — cover **2,000 exposed
   versions and 82 packages. This union is one `algo.MSpaths` call: sources
   resolved through HydraDB's property index, no client-side fan-out. That's
   the 42-package worm case, batched."
4. (Optional, if time) click the `rc@1.2.8` chip: "the 2021 ua-parser-js hijack
   — 419 exposed versions on its own."

## Take 5 (2:45-3:00) — Wrap
"Why HydraDB? Blast radius is a graph traversal, not a similarity search —
sub-second at six hops. The model is versioned and temporal, storage is
object-backed and cheap. Without HydraDB this is a pile of per-package API
calls and a hand-rolled closure: slower, and no time-travel. Blastfall —
compromised at 09:00, exposed by 09:06. Repo, attribution, and the full model
are on GitHub."

## Before recording
- `scripts/up.sh` once; open `http://localhost:8123`.
- Verify all five featured chips load (needs the graph ingested).
- Recording software of choice; unlisted YouTube link for submission.

## Expected live numbers (sanity anchors)
| Scenario | exposed versions | services |
|---|---|---|
| `ms@2.1.3`, hops 6 | ~1,751 | 4 of 5 |
| `rc@1.2.8`, hops 5 | ~419 | — |
| `colors@1.4.0`, hops 5 | ~80 | — |
| `rc, colors`, hops 5 (MSpaths union) | ~2,000 | — |
| `debug@4.4.3`, hops 5 | ~549 | 4 of 5 |

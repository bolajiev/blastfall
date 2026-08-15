"""Query layer for the Blastfall demo app."""

import json
import os
import urllib.request

from ingest.hydradb import TOKEN, GRAPH_URL

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
IDMAP_PATH = os.path.join(DATA_DIR, "idmap.json")

_idmap = None
_rev = None


def _load_idmap():
    global _idmap, _rev
    if _idmap is None:
        with open(IDMAP_PATH) as f:
            data = json.load(f)
        _idmap = data["map"]
        _rev = {v: k for k, v in data["map"].items()}
    return _idmap, _rev


def _parse_spec(spec):
    """'name@version' or bare 'name'. Returns (name, version|None)."""
    if "@" in spec:
        return spec.split("@", 1)[0], spec.split("@", 1)[1]
    return spec, None


def _lookup(spec):
    m, _ = _load_idmap()
    return m.get(spec)


def lookup_package(name):
    return _lookup(f"pkg:{name}")


def lookup_version(name, version):
    return _lookup(f"{name}@{version}")


def version_published_at(name, version):
    vid = lookup_version(name, version)
    if vid is None:
        return None
    q = "MATCH (v:Version {id: $id}) RETURN v.publishedAt AS at"
    r = _post_raw({"cell_id": "cell-0", "query": q, "parameters": {"id": vid}})
    if r.get("rows"):
        return r["rows"][0][0]["value"]
    return None


def _post_raw(body):
    req = urllib.request.Request(
        GRAPH_URL,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "X-Graph-Namespace": "default",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def search_packages(prefix, limit=20):
    q = "MATCH (p:Package) WHERE p.name STARTS WITH $q RETURN p.name AS name ORDER BY p.name LIMIT $limit"
    r = _post_raw({
        "cell_id": "cell-0", "query": q, "page_size": 100,
        "parameters": {"q": prefix, "limit": limit},
    })
    return [row[0]["value"] for row in r.get("rows", [])]


def package_versions(name, limit=50):
    pid = lookup_package(name)
    if pid is None:
        return []
    q = "MATCH (p:Package {id: $id})-[:HAS_VERSION]->(v:Version) RETURN v.version AS ver, v.publishedAt AS at ORDER BY v.version DESC LIMIT $limit"
    r = _post_raw({
        "cell_id": "cell-0", "query": q, "page_size": 100,
        "parameters": {"id": pid, "limit": limit},
    })
    return [{"version": row[0]["value"], "publishedAt": row[1]["value"]} for row in r.get("rows", [])]


def _reachable_ids(source_id, max_len, direction, path_count=100000):
    """All node ids reachable from source via DEPENDS_ON, traversing `direction`."""
    _, rev = _load_idmap()
    ids = set()
    cursor = None
    query_id = None
    q = (
        "CALL algo.SSpaths({sourceNode: $s, relTypes: ['DEPENDS_ON'], "
        "maxLen: %d, relDirection: '%s', pathCount: %d}) YIELD path RETURN path"
        % (max_len, direction, path_count)
    )
    while True:
        body = {"cell_id": "cell-0", "query": q, "parameters": {"s": source_id}}
        if cursor is not None:
            body["cursor"] = cursor
        if query_id:
            body["query_id"] = query_id
        r = _post_raw(body)
        query_id = r.get("query_id", query_id)
        for row in r.get("rows", []):
            for node in row[0]["value"]["nodes"]:
                ids.add(node["id"])
        cursor = r.get("next_cursor")
        if not cursor or not r.get("rows"):
            break
    return ids


def blast_radius(spec, max_len=6, direction="incoming", include_services=True):
    """Blast radius of name@version: exposed versions, packages, services."""
    _, rev = _load_idmap()
    name, version = _parse_spec(spec)
    vid = lookup_version(name, version)
    if vid is None:
        return None
    ids = _reachable_ids(vid, max_len, direction)
    ids.discard(vid)
    versions = []
    packages = set()
    services = set()
    for i in ids:
        key = rev.get(i)
        if not key:
            continue
        if key.startswith("pkg:"):
            packages.add(key[4:])
        elif key.startswith("srv:"):
            services.add(key[4:])
        else:
            versions.append(key)
    packages |= {v.split("@")[0] for v in versions}
    return {
        "name": name,
        "version": version,
        "exposed_version_count": len(versions),
        "exposed_package_count": len(packages),
        "exposed_packages": sorted(packages),
        "exposed_services": sorted(services),
        "maxLen": max_len,
    }


def direct_dependents(spec, limit=50):
    _, rev = _load_idmap()
    name, version = _parse_spec(spec)
    vid = lookup_version(name, version)
    if vid is None:
        return None
    q = "MATCH (v:Version)-[:DEPENDS_ON]->(c:Version {id: $id}) RETURN v.name AS name, v.version AS ver, v.publishedAt AS at ORDER BY v.publishedAt DESC LIMIT $limit"
    r = _post_raw({"cell_id": "cell-0", "query": q, "page_size": 100,
                   "parameters": {"id": vid, "limit": limit}})
    rows = [{"name": row[0]["value"], "version": row[1]["value"], "publishedAt": row[2]["value"]}
            for row in r.get("rows", [])]
    count_q = "MATCH (v:Version)-[:DEPENDS_ON]->(c:Version {id: $id}) RETURN count(*) AS n"
    rc = _post_raw({"cell_id": "cell-0", "query": count_q, "parameters": {"id": vid}})
    total = rc["rows"][0][0]["value"] if rc.get("rows") else 0
    return {"total": total, "rows": rows}


def resolution_window(spec, after, before, limit=50):
    name, version = _parse_spec(spec)
    vid = lookup_version(name, version)
    if vid is None:
        return None
    q = ("MATCH (c:Version {id: $id}), (v:Version)-[:DEPENDS_ON]->(c) "
         "WHERE v.publishedAt >= $after AND v.publishedAt <= $before "
         "RETURN v.name AS name, v.version AS ver, v.publishedAt AS at "
         "ORDER BY v.publishedAt DESC LIMIT $limit")
    r = _post_raw({"cell_id": "cell-0", "query": q, "page_size": 100,
                   "parameters": {"id": vid, "after": after, "before": before, "limit": limit}})
    return [{"name": row[0]["value"], "version": row[1]["value"], "publishedAt": row[2]["value"]}
            for row in r.get("rows", [])]


def typosquats(name):
    pid = lookup_package(name)
    if pid is None:
        return []
    q = "MATCH (p:Package {id: $id})-[:TYPOSQUAT]->(c:Package) RETURN c.name AS name ORDER BY c.name"
    r = _post_raw({"cell_id": "cell-0", "query": q, "parameters": {"id": pid}})
    return [row[0]["value"] for row in r.get("rows", [])]


def shared_maintainers(name):
    """Other packages sharing a maintainer with `name`."""
    pid = lookup_package(name)
    if pid is None:
        return {}
    q = ("MATCH (p:Package {id: $id})<-[:MAINTAINS]-(m:Maintainer)-[:MAINTAINS]->(other:Package) "
         "WHERE other.name <> $name RETURN m.name AS maintainer, other.name AS pkg ORDER BY other.name")
    r = _post_raw({"cell_id": "cell-0", "query": q, "page_size": 4000,
                   "parameters": {"id": pid, "name": name}})
    out = {}
    for row in r.get("rows", []):
        m, p = row[0]["value"], row[1]["value"]
        out.setdefault(m, []).append(p)
    return out


def exposed_services(compromised_spec, max_len=8):
    """Which org services are transitively exposed by a compromised package@version."""
    _, rev = _load_idmap()
    name, version = _parse_spec(compromised_spec)
    vid = lookup_version(name, version)
    if vid is None:
        return None
    ids = _reachable_ids(vid, max_len, "incoming")
    services = sorted(rev.get(i)[4:] for i in ids if rev.get(i, "").startswith("srv:"))
    return {"services": services, "maxLen": max_len}


def subgraph(spec, max_len=6, path_count=200):
    """Sampled blast-radius subgraph as nodes/edges for visualization."""
    _, rev = _load_idmap()
    name, version = _parse_spec(spec)
    vid = lookup_version(name, version)
    if vid is None:
        return None
    nodes = {vid: {"id": vid, "label": f"{name}@{version}", "kind": "compromised"}}
    edges = set()
    cursor = None
    query_id = None
    q = (
        "CALL algo.SSpaths({sourceNode: $s, relTypes: ['DEPENDS_ON'], "
        "maxLen: %d, relDirection: 'incoming', pathCount: %d}) YIELD path RETURN path"
        % (max_len, path_count)
    )
    while True:
        body = {"cell_id": "cell-0", "query": q, "parameters": {"s": vid}}
        if cursor is not None:
            body["cursor"] = cursor
        if query_id:
            body["query_id"] = query_id
        r = _post_raw(body)
        query_id = r.get("query_id", query_id)
        for row in r.get("rows", []):
            path_nodes = row[0]["value"]["nodes"]
            for i, node in enumerate(path_nodes):
                nid = node["id"]
                key = rev.get(nid)
                if nid not in nodes:
                    kind = "service" if key.startswith("srv:") else "version"
                    nodes[nid] = {"id": nid, "label": key, "kind": kind}
                if i > 0:
                    edges.add((path_nodes[i - 1]["id"], nid))
        cursor = r.get("next_cursor")
        if not cursor or not r.get("rows"):
            break
    return {"nodes": list(nodes.values()), "edges": [{"src": s, "dst": d} for s, d in edges]}

"""Minimal HydraDB HTTPS query client."""

import json
import os
import time
import urllib.error
import urllib.request

TOKEN = os.environ.get("HYDRADB_TOKEN", "local-development-token-32-bytes")
GRAPH_URL = os.environ.get("HYDRADB_GRAPH_URL", "http://127.0.0.1:8443/v1/graphs/default/query")


def post(cell, query, parameters=None, timeout=300):
    body = {"cell_id": cell, "query": query}
    if parameters:
        body["parameters"] = parameters
    req = urllib.request.Request(
        GRAPH_URL,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "X-Graph-Namespace": "default",
            "Content-Type": "application/json",
        },
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (408, 429, 500, 503):
                time.sleep(1 * (attempt + 1))
                continue
            raise RuntimeError(f"{e.code}: {e.read().decode()[:400]}")
    raise RuntimeError("repeated HydraDB failures")


class IdMap:
    def __init__(self, path):
        self.path = path
        self.map = {}
        self.next_id = 1
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            self.map = data["map"]
            self.next_id = data["next_id"]

    def get(self, key):
        if key not in self.map:
            self.map[key] = self.next_id
            self.next_id += 1
        return self.map[key]

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump({"map": self.map, "next_id": self.next_id}, f)


def ingest_nodes(nodes, label, batch=800):
    """nodes: iterable of dicts, each with 'id' plus property fields."""
    rows = list(nodes)
    props = [k for k in rows[0].keys() if k != "id"] if rows else []
    set_clause = ", ".join(f"n.{k} = row.{k}" for k in props)
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        post(
            "cell-0",
            f"UNWIND $rows AS row MERGE (n {{id: row.id}}) SET n:{label}, {set_clause}",
            {"rows": chunk},
        )
        print(f"  {label} nodes [{i}:{i + len(chunk)}]")


def ingest_edges(edges, label, src_label, dst_label, batch=800):
    """edges: iterable of dicts with 'src','dst', plus optional property fields."""
    rows = list(edges)
    if rows:
        props = [k for k in rows[0].keys() if k not in ("src", "dst")]
        if "id" not in props:
            props.insert(0, "id")
        for n, row in enumerate(rows):
            if "id" not in row:
                row["id"] = n + 1
    else:
        props = []
    prop_str = ""
    if props:
        extra = ", ".join(f"{k}: row.{k}" for k in props)
        prop_str = f" {{{extra}}}"
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        post(
            "cell-0",
            f"UNWIND $rows AS row MATCH (s:{src_label} {{id: row.src}}), (d:{dst_label} {{id: row.dst}}) "
            f"CREATE (s)-[:{label}{prop_str}]->(d)",
            {"rows": chunk},
        )
        print(f"  {label} edges [{i}:{i + len(chunk)}]")

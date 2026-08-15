"""Demo org manifest: ingest `Service` nodes wired into the versioned dependency graph.

Each service is modeled as a Service node with DEPENDS_ON edges to the resolved
versions of its declared dependencies. Because Service->Version edges use the
same DEPENDS_ON edge type as Version->Version, a reverse traversal from any
compromised version automatically surfaces the exposed services.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))

from ingest import hydradb, semver_range
from app import graph

ORG = {
    "payments-api": {
        "express": "^5.2.1",
        "jsonwebtoken": "^9.0.0",
        "stripe": "^17.0.0",
        "winston": "^3.0.0",
        "dotenv": "^16.0.0",
        "axios": "^1.0.0",
        "ms": "^2.1.3",
        "uuid": "^14.0.0",
    },
    "auth-service": {
        "express": "^5.2.1",
        "jsonwebtoken": "^9.0.0",
        "bcryptjs": "^3.0.0",
        "validator": "^13.0.0",
        "pg": "^8.0.0",
        "dotenv": "^16.0.0",
        "ms": "^2.1.3",
    },
    "web-dashboard": {
        "next": "^16.0.0",
        "react": "^19.0.0",
        "react-dom": "^19.0.0",
        "axios": "^1.0.0",
        "dayjs": "^1.0.0",
        "lodash": "^4.0.0",
        "styled-components": "^6.0.0",
    },
    "reports-worker": {
        "bull": "^4.0.0",
        "nodemailer": "^6.0.0",
        "xlsx": "^0.18.0",
        "moment": "^2.0.0",
        "pg": "^8.0.0",
        "debug": "^4.0.0",
    },
    "search-api": {
        "fastify": "^5.0.0",
        "axios": "^1.0.0",
        "openai": "^7.0.0",
        "mongoose": "^9.0.0",
        "ioredis": "^5.0.0",
        "chalk": "^6.0.0",
    },
}


def resolve_dep(dep_name, req):
    """Highest in-universe version satisfying the range, or None."""
    versions = graph.package_versions(dep_name, limit=500)
    best = None
    for item in versions:
        v = item["version"]
        if semver_range.resolves(req, v):
            if best is None or _version_tuple(v) > _version_tuple(best):
                best = v
    return best


def _version_tuple(v):
    parts = []
    for p in v.split(".")[:3]:
        try:
            parts.append(int(p))
        except ValueError:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def ingest_org():
    idmap = hydradb.IdMap(os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "idmap.json"))
    service_rows = []
    edge_rows = []
    for sname, deps in ORG.items():
        sid = idmap.get(f"srv:{sname}")
        service_rows.append({"id": sid, "name": sname})
        for dep, req in deps.items():
            resolved = resolve_dep(dep, req)
            vid = graph.lookup_version(dep, resolved or "")
            if vid is None:
                print(f"  [skip] {sname} -> {dep} (not resolved in universe)")
                continue
            edge_rows.append({"src": sid, "dst": vid, "requirement": req})
            print(f"  {sname} -> {dep}@{resolved}")
    idmap.save()
    hydradb.ingest_nodes(service_rows, "Service")
    hydradb.ingest_edges(edge_rows, "DEPENDS_ON", "Service", "Version")
    print(f"Ingested {len(service_rows)} services, {len(edge_rows)} Service->Version edges.")


if __name__ == "__main__":
    ingest_org()

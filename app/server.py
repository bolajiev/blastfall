"""Blastfall — supply-chain blast radius on the HydraDB versioned dependency graph."""

import os
import sys

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import graph

app = FastAPI(title="Blastfall")


class Compromise(BaseModel):
    name: str
    version: str
    maxLen: int = 6
    attackTime: str = ""


@app.get("/")
def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


@app.get("/api/packages")
def packages(q: str = "", limit: int = 20):
    return {"packages": graph.search_packages(q, limit)}


@app.get("/api/versions/{name}")
def versions(name: str):
    return {"versions": graph.package_versions(name)}


@app.post("/api/compromise")
def compromise(body: Compromise):
    spec = f"{body.name}@{body.version}"
    br = graph.blast_radius(spec, max_len=body.maxLen)
    if br is None:
        return {"error": f"unknown package@version: {spec}"}
    dd = graph.direct_dependents(spec)
    typos = graph.typosquats(body.name)
    mnts = graph.shared_maintainers(body.name)
    window = []
    if body.attackTime:
        published = graph.version_published_at(body.name, body.version)
        if published:
            window = graph.resolution_window(spec, after=published, before=body.attackTime)
    sub = graph.subgraph(spec, max_len=min(body.maxLen, 4), path_count=150)
    return {
        "blast_radius": br,
        "direct_dependents": dd,
        "typosquats": typos,
        "shared_maintainers": mnts,
        "resolution_window": window,
        "subgraph": sub,
    }

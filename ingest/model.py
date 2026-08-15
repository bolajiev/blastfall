"""Build the versioned dependency graph model from npm registry docs."""

from . import semver_range

MAINTAINER_PREFIX = "mnt:"
PACKAGE_PREFIX = "pkg:"
VERSION_PREFIX = ""


def version_key(name, version):
    return f"{name}@{version}"


def package_key(name):
    return f"{PACKAGE_PREFIX}{name}"


def maintainer_key(name):
    return f"{MAINTAINER_PREFIX}{name}"


def build_model(docs, idmap, version_limit_per_package=400):
    """Turn registry docs into node/edge row lists for HydraDB."""
    version_nodes = {}
    package_nodes = {}
    maintainer_nodes = {}
    has_version_edges = set()
    declares_edges = set()   # (version_id, package_id, requirement)
    dependents_count = {}

    # sorted version keys per package, for resolution
    versions_by_pkg = {}

    for name, doc in docs.items():
        if not doc or not isinstance(doc, dict):
            continue
        versions = doc.get("versions", {})
        time_map = doc.get("time", {})
        all_version_names = list(versions.keys())
        if len(all_version_names) > version_limit_per_package:
            # keep latest N published versions
            all_version_names = sorted(
                all_version_names, key=lambda v: time_map.get(v, ""), reverse=True
            )[:version_limit_per_package]
        versions_by_pkg[name] = all_version_names
        dependents_count[name] = 0

        for m in doc.get("maintainers", []):
            mname = m.get("name")
            if not mname:
                continue
            mid = idmap.get(maintainer_key(mname))
            maintainer_nodes[mid] = {"id": mid, "name": mname}

        pkg_id = idmap.get(package_key(name))
        package_nodes[pkg_id] = {
            "id": pkg_id,
            "name": name,
            "latest": (doc.get("dist-tags") or {}).get("latest", ""),
        }

        for vname in all_version_names:
            ver = versions[vname]
            published_at = time_map.get(vname, "")
            vid = idmap.get(version_key(name, vname))
            version_nodes[vid] = {
                "id": vid,
                "name": name,
                "version": vname,
                "publishedAt": published_at,
            }
            has_version_edges.add((pkg_id, vid))

            deps = {}
            deps.update(ver.get("dependencies", {}))
            deps.update(ver.get("optionalDependencies", {}))
            for dep_name, req in deps.items():
                dep_name = dep_name.split("/")[0] if dep_name.startswith("@") else dep_name
                if dep_name.startswith("@") or dep_name not in dependents_count:
                    continue
                dependents_count[dep_name] += 1
                declares_edges.add((vid, idmap.get(package_key(dep_name)), req))

    # patch maintainer edges with package ids
    maintains_rows = set()
    for name, doc in docs.items():
        if not doc or not isinstance(doc, dict):
            continue
        pkg_id = idmap.get(package_key(name))
        for m in doc.get("maintainers", []):
            mname = m.get("name")
            if not mname:
                continue
            maintains_rows.add((idmap.get(maintainer_key(mname)), pkg_id))

    # resolution pass: Version -> Version resolved edges
    import bisect

    resolved_edges = set()
    by_name_versions = {}
    by_name_published = {}
    for name, vnames in versions_by_pkg.items():
        vs = sorted(
            vnames, key=lambda v: version_nodes[idmap.get(version_key(name, v))]["publishedAt"]
        )
        by_name_versions[name] = vs
        by_name_published[name] = [
            version_nodes[idmap.get(version_key(name, v))]["publishedAt"] for v in vs
        ]

    for name, vnames in versions_by_pkg.items():
        for vname in vnames:
            vid = idmap.get(version_key(name, vname))
            published_at = version_nodes[vid]["publishedAt"]
            ver = docs[name]["versions"][vname]
            deps = {}
            deps.update(ver.get("dependencies", {}))
            deps.update(ver.get("optionalDependencies", {}))
            for dep_name, req in deps.items():
                dep_name = dep_name.split("/")[0] if dep_name.startswith("@") else dep_name
                if dep_name.startswith("@") or dep_name not in by_name_versions:
                    continue
                target = _resolve(published_at, req, dep_name, by_name_versions,
                                  by_name_published, idmap, version_nodes)
                if target is not None:
                    resolved_edges.add((vid, target, req))

    # typosquat pass
    typosquat_edges = set()
    popular = {name for name, cnt in dependents_count.items() if cnt >= 10}
    popular |= set(docs.keys())
    universe_names = set(versions_by_pkg.keys())
    popular_names = {n for n in popular if n in universe_names}
    for pname in popular_names:
        for cand in _typosquat_candidates(pname, universe_names):
            if cand != pname:
                typosquat_edges.add((idmap.get(package_key(pname)), idmap.get(package_key(cand)), 1))

    return {
        "package_nodes": list(package_nodes.values()),
        "version_nodes": list(version_nodes.values()),
        "maintainer_nodes": list(maintainer_nodes.values()),
        "has_version_edges": [{"src": s, "dst": d} for s, d in has_version_edges],
        "declares_edges": [{"src": s, "dst": d, "requirement": r} for s, d, r in declares_edges],
        "resolved_edges": [{"src": s, "dst": d, "requirement": r} for s, d, r in resolved_edges],
        "maintains_edges": [{"src": s, "dst": d} for s, d in maintains_rows],
        "typosquat_edges": [{"src": s, "dst": d, "distance": dist} for s, d, dist in typosquat_edges],
        "dependents_count": dependents_count,
    }


def _resolve(published_at, requirement, dep_name, by_name_versions,
             by_name_published, idmap, version_nodes):
    """Highest version of dep_name published <= published_at satisfying the range."""
    import bisect
    vs = by_name_versions[dep_name]
    published = by_name_published[dep_name]
    idx = bisect.bisect_right(published, published_at)
    for i in range(idx - 1, -1, -1):
        cand = vs[i]
        if semver_range.resolves(requirement, cand):
            return idmap.get(version_key(dep_name, cand))
    return None


_ALPHANUM = "abcdefghijklmnopqrstuvwxyz0123456789-._"


def _typosquat_candidates(name, universe):
    """All in-universe names within edit distance 1 of `name`."""
    found = set()
    n = len(name)
    # deletions
    for i in range(n):
        found.add(name[:i] + name[i + 1:])
    # transpositions
    for i in range(n - 1):
        found.add(name[:i] + name[i + 1] + name[i] + name[i + 2:])
    # substitutions and insertions
    for i in range(n + 1):
        for ch in _ALPHANUM:
            found.add(name[:i] + ch + name[i + 1:])
            found.add(name[:i] + ch + name[i:])
    return [f for f in found if f in universe]

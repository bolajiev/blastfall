import os

from . import hydradb, model
from .registry import SEED, collect_closure

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
MAX_PACKAGES = int(os.environ.get("MAX_PACKAGES", "2500"))


def run():
    print(f"[1/4] collecting closure up to {MAX_PACKAGES} packages (cached)")
    docs = collect_closure(SEED, MAX_PACKAGES)
    print(f"  -> {len(docs)} package docs")

    idmap = hydradb.IdMap(os.path.join(DATA_DIR, "idmap.json"))
    print("[2/4] building model")
    m = model.build_model(docs, idmap)
    print(f"  packages={len(m['package_nodes'])} versions={len(m['version_nodes'])} "
          f"maintainers={len(m['maintainer_nodes'])}")
    print(f"  edges: HAS_VERSION={len(m['has_version_edges'])} DECLARES={len(m['declares_edges'])} "
          f"DEPENDS_ON={len(m['resolved_edges'])} MAINTAINS={len(m['maintains_edges'])} "
          f"TYPOSQUAT={len(m['typosquat_edges'])}")
    idmap.save()

    print("[3/4] ingesting nodes")
    hydradb.ingest_nodes(m["package_nodes"], "Package")
    hydradb.ingest_nodes(m["version_nodes"], "Version")
    hydradb.ingest_nodes(m["maintainer_nodes"], "Maintainer")

    print("[4/4] ingesting edges")
    hydradb.ingest_edges(m["has_version_edges"], "HAS_VERSION", "Package", "Version")
    hydradb.ingest_edges(m["declares_edges"], "DECLARES", "Version", "Package")
    hydradb.ingest_edges(m["resolved_edges"], "DEPENDS_ON", "Version", "Version")
    hydradb.ingest_edges(m["maintains_edges"], "MAINTAINS", "Maintainer", "Package")
    hydradb.ingest_edges(m["typosquat_edges"], "TYPOSQUAT", "Package", "Package")

    print("\nIngest complete.")


if __name__ == "__main__":
    run()

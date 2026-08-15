#!/usr/bin/env bash
# Bring up Blastfall: HydraDB (docker) + graph ingest + FastAPI app.
# Usage: scripts/up.sh [max_packages]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MAX_PACKAGES="${1:-2500}"
PORT="${PORT:-8123}"
DATA_DIR="$ROOT/hydradb-data"
TOKEN='local-development-token-32-bytes'
GHCR="ghcr.io/hydra-db/hydradb:latest"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required (or build hydradb from source and adapt this script)"
  exit 1
fi

echo "[1/4] starting HydraDB"
docker rm -f hydradb >/dev/null 2>&1 || true
mkdir -p "$DATA_DIR/store" "$DATA_DIR/cache"
printf '%s\n' "$TOKEN" > "$DATA_DIR/auth-token"
docker run -d --name hydradb \
  --user "$(id -u):$(id -g)" \
  -p 7687:7687 -p 8443:8443 -p 9090:9090 \
  -v "$DATA_DIR:/data" \
  -e CLOUD_PROVIDER=local \
  -e LOCAL_PATH=/data/store \
  -e GRAPH_NAMESPACE=default \
  -e GRAPH_ID=default \
  -e GRAPH_CELL_ID=cell-0 \
  -e GRAPH_CELLS=cell-0 \
  -e GRAPH_NODE_ID=node-0 \
  -e GRAPH_BOLT_NODE_ADDRESSES=node-0=127.0.0.1:7687 \
  -e GRAPH_ADVERTISED_BOLT_ADDR=127.0.0.1:7687 \
  -e GRAPH_DATA_CACHE_DIR=/data/cache \
  -e GRAPH_AUTH_TOKEN_FILE=/data/auth-token \
  -e GRAPH_ALLOW_PLAINTEXT=true \
  -e RUST_MIN_STACK=33554432 \
  "$GHCR" >/dev/null

echo "  waiting for /readyz"
for i in $(seq 1 60); do
  curl -fsS http://127.0.0.1:9090/readyz >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS http://127.0.0.1:9090/readyz >/dev/null 2>&1 || { echo "  hydradb failed to become ready"; exit 1; }
echo "  hydradb ready"

PY=python3
[ -x ".venv/bin/python" ] && PY=".venv/bin/python"

if ! "$PY" -c "import fastapi" 2>/dev/null; then
  echo "[2/4] installing python deps"
  "$PY" -m pip install -q -r requirements.txt
fi

echo "[3/4] checking graph / ingesting if empty"
if ! "$PY" -c "
from ingest.hydradb import post
r = post('cell-0', 'MATCH (p:Package) RETURN count(*) AS n')
print('packages:', r['rows'][0][0]['value'])
" 2>/dev/null | grep -q "packages: [1-9]"; then
  echo "  ingesting npm universe (MAX_PACKAGES=$MAX_PACKAGES)..."
  MAX_PACKAGES="$MAX_PACKAGES" "$PY" -m ingest.build_graph
  echo "  ingesting demo org services..."
  "$PY" -m app.services
else
  echo "  graph already populated"
fi

echo "[4/4] starting app on :$PORT"
exec "$PY" -m uvicorn app.server:app --host 0.0.0.0 --port "$PORT"

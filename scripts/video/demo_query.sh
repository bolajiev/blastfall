#!/usr/bin/env bash
# Blastfall demo query: compromise name@version and print the headline exposure.
# Usage: scripts/video/demo_query.sh ms@2.1.3
set -euo pipefail

SPEC="${1:-ms@2.1.3}"
NAME="${SPEC%%@*}"
VERSION="${SPEC#*@}"

curl -s -X POST http://localhost:8123/api/compromise \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"${NAME}\",\"version\":\"${VERSION}\",\"maxLen\":5}" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
if 'error' in d:
    print('error:', d['error']); sys.exit(0)
br = d['blast_radius']
print(f\"[compromised] {br['name']}@{br['version']}\")
print(f\"exposed versions : {br['exposed_version_count']}\")
print(f\"exposed packages : {br['exposed_package_count']}\")
print(f\"services exposed : {', '.join(br['exposed_services']) or 'none'}\")
print(f\"direct dependents: {d['direct_dependents']['total']}\")
"

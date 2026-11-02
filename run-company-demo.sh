#!/usr/bin/env bash
set -euo pipefail
# Usage: bash run-company-demo.sh [port], no downloads or data writes.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PORT="${1:-8059}"
echo "Company Communication Demo (FICTIONAL): 77 roles, 169 directed sender-to-recipient links."
echo "Open http://127.0.0.1:${PORT}/ when the server starts."
echo "Choose Network / Fully Expanded for this general communication graph."
exec python -m jaal_topology \
  --edges examples/company_communications.csv \
  --metadata examples/company_people.csv \
  --port "$PORT"

#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

bash ci/check-phase8.sh
source ci/python-env.sh
export PYTHONPATH="$repo_root/cli/src:$PYTHONPATH"

python3 -m unittest local-api/tests/test_local_api.py cli/tests/test_cli.py

echo "Phase 9 local API bridge checks passed."

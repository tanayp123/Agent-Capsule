#!/usr/bin/env bash
set -euo pipefail

deps_dir="${TMPDIR:-/tmp}/agent-capsule-python-deps"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$deps_dir"

if ! PYTHONPATH="$deps_dir" python3 -c "import cryptography" >/dev/null 2>&1; then
  PIP_DISABLE_PIP_VERSION_CHECK=1 python3 -m pip install --quiet --target "$deps_dir" "cryptography>=42.0.0"
fi

export PYTHONPATH="$deps_dir:$repo_root/local-api/src:$repo_root/policy-engine/src:$repo_root/sdk-python/src${PYTHONPATH:+:$PYTHONPATH}"

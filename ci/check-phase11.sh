#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

bash ci/check-phase10.sh
source ci/python-env.sh
export PYTHONPATH="$repo_root/cli/src:$PYTHONPATH"

python3 -m unittest cli/tests/test_cli.py

tmp_dir="${TMPDIR:-/tmp}/agent-capsule-phase11-build"
rm -rf "$tmp_dir"
mkdir -p "$tmp_dir"

cat >"$tmp_dir/requirements.txt" <<'REQ'
agent-capsule==0.1.0
REQ

cat >"$tmp_dir/claim-classification.prompt" <<'PROMPT'
Private claim classification prompt that must never appear in manifest output.
PROMPT

cat >"$tmp_dir/crm-tool.schema.json" <<'JSON'
{"type":"object","properties":{"account_id":{"type":"string"}}}
JSON

python3 -m agent_capsule_cli build \
  --source-dir "$tmp_dir" \
  --policy fixtures/policies/crm-policy.json \
  --output "$tmp_dir/capsule-manifest.json" \
  --build-report "$tmp_dir/build-report.json" \
  --prompt-template claim_classification=claim-classification.prompt \
  --tool-schema crm.upsert_account:1.0.0:crm-tool.schema.json \
  --model-provider "Example Model" \
  --model "example-large" \
  --required-secret MODEL_PROVIDER_API_KEY \
  --usage-meter claim_count:claim \
  --signing-key phase11-test-signing-key \
  --key-id phase11-test-key \
  --json >"$tmp_dir/build-output.json"

PYTHONPATH=ci python3 ci/validate-json-file.py schemas/manifest.schema.json "$tmp_dir/capsule-manifest.json"

python3 -m agent_capsule_cli manifest inspect "$tmp_dir/capsule-manifest.json" --json >"$tmp_dir/inspect-output.json"

signature_value="$(python3 - "$tmp_dir/capsule-manifest.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["signature"]["value"])
PY
)"

if grep -q "Private claim classification prompt" "$tmp_dir/capsule-manifest.json" "$tmp_dir/build-report.json" "$tmp_dir/build-output.json" "$tmp_dir/inspect-output.json"; then
  echo "Capsule build leaked prompt template plaintext" >&2
  exit 1
fi

if grep -q "$signature_value" "$tmp_dir/build-report.json" "$tmp_dir/build-output.json" "$tmp_dir/inspect-output.json"; then
  echo "Capsule build or inspect leaked signature value" >&2
  exit 1
fi

echo "Phase 11 capsule build checks passed."

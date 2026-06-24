#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

bash ci/check-phase9.sh
source ci/python-env.sh
export PYTHONPATH="$repo_root/cli/src:$PYTHONPATH"

python3 -m unittest discover -s sdk-python/tests

sample_dir="${TMPDIR:-/tmp}/agent-capsule-phase10-guard-sample"
rm -rf "$sample_dir"
mkdir -p "$sample_dir"

set +e
AGENT_CAPSULE_MODE=guard \
AGENT_CAPSULE_POLICY="$repo_root/fixtures/policies/restrictive-policy.json" \
python3 examples/claims-triage-python/claims_triage.py --trace-dir "$sample_dir" \
  >"$sample_dir/stdout.txt" 2>"$sample_dir/stderr.txt"
sample_status=$?
set -e

if [[ "$sample_status" -eq 0 ]]; then
  echo "Guard mode sample unexpectedly succeeded under restrictive policy" >&2
  exit 1
fi

trace_path="$(find "$sample_dir/metadata" -name '*.json' -print -quit)"
if [[ -z "$trace_path" ]]; then
  echo "Guard mode sample did not write trace metadata" >&2
  exit 1
fi

PYTHONPATH=ci python3 ci/validate-json-file.py schemas/trace.schema.json "$trace_path"

python3 - "$trace_path" <<'PY'
import json
import sys
from pathlib import Path

trace = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
blocked = [
    span for span in trace["spans"]
    if span["component_name"] == "classify-claim"
]
if len(blocked) != 1:
    raise SystemExit("expected one classify-claim span")
span = blocked[0]
if span["status"] != "blocked":
    raise SystemExit("expected classify-claim span to be blocked")
if span["policy_decision"]["action"] != "block":
    raise SystemExit("expected blocked policy decision")
if span["policy_decision"]["reason"] != "undeclared high-risk egress":
    raise SystemExit("expected undeclared high-risk egress reason")
PY

for raw_value in \
  "claimant@example.com" \
  "Neck pain reported after accident" \
  "Rear-end collision at low speed" \
  "Claim requires review because medical context is present"
do
  if grep -R -q "$raw_value" "$sample_dir/stdout.txt" "$sample_dir/stderr.txt" "$sample_dir/metadata"; then
    echo "Guard mode output leaked raw payload value: $raw_value" >&2
    exit 1
  fi
done

echo "Phase 10 Guard Mode checks passed."

#!/usr/bin/env bash
set -euo pipefail

bash ci/check-phase1.sh
source ci/python-env.sh
python3 -m unittest sdk-python/tests/test_observe.py

sample_dir="${TMPDIR:-/tmp}/agent-capsule-phase2-sample"
rm -rf "$sample_dir"
mkdir -p "$sample_dir"

trace_path="$(
  python3 examples/claims-triage-python/claims_triage.py --trace-dir "$sample_dir"
)"

PYTHONPATH=ci python3 ci/validate-json-file.py schemas/trace.schema.json "$trace_path"

for raw_value in \
  "claimant@example.com" \
  "Neck pain reported after accident" \
  "Rear-end collision at low speed" \
  "Claim requires review because medical context is present"
do
  if grep -R -q "$raw_value" "$sample_dir"; then
    echo "Generated trace contains raw payload value: $raw_value" >&2
    exit 1
  fi
done

echo "Phase 2 Python observe-mode checks passed."

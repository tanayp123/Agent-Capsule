#!/usr/bin/env bash
set -euo pipefail

bash ci/check-phase2.sh
source ci/python-env.sh
python3 -m unittest sdk-python/tests/test_trace_store.py

sample_dir="${TMPDIR:-/tmp}/agent-capsule-phase3-sample"
rm -rf "$sample_dir"
mkdir -p "$sample_dir"

trace_path="$(
  python3 examples/claims-triage-python/claims_triage.py --trace-dir "$sample_dir"
)"

test -f "$trace_path"
test -d "$sample_dir/metadata"
test -d "$sample_dir/payloads"
test -d "$sample_dir/payload-index"
test -f "$sample_dir/keys/local.key"

encrypted_count="$(find "$sample_dir/payloads" -name '*.enc' -type f | wc -l | tr -d ' ')"
if [ "$encrypted_count" -lt 1 ]; then
  echo "Expected encrypted payload sidecars" >&2
  exit 1
fi

for raw_value in \
  "claimant@example.com" \
  "Neck pain reported after accident" \
  "Rear-end collision at low speed" \
  "Claim requires review because medical context is present"
do
  if grep -R -q "$raw_value" "$sample_dir"; then
    echo "Trace store contains raw payload value: $raw_value" >&2
    exit 1
  fi
done

echo "Phase 3 encrypted trace-store checks passed."

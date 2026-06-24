#!/usr/bin/env bash
set -euo pipefail

bash ci/check-phase5.sh
source ci/python-env.sh
export PYTHONPATH="$PWD/cli/src:$PYTHONPATH"

python3 -m unittest sdk-python/tests/test_safe_trace.py
python3 -m unittest cli/tests/test_cli.py

PYTHONPATH=ci python3 ci/validate-json-file.py \
  schemas/safe-trace.schema.json \
  agent-capsule-console/fixtures/safe-trace-import.json

repo_root="$PWD"
tmp_dir="${TMPDIR:-/tmp}/agent-capsule-phase6-safe-export"
safe_trace_path="$tmp_dir/safe-trace.json"
rm -rf "$tmp_dir"
mkdir -p "$tmp_dir"

(
  cd "$tmp_dir"
  python3 -m agent_capsule_cli init --json >/tmp/agent-capsule-phase6-init.json
  python3 -m agent_capsule_cli run --mode observe -- python3 "$repo_root/examples/claims-triage-python/claims_triage.py" >/tmp/agent-capsule-phase6-run.txt
  python3 -m agent_capsule_cli trace list --json >/tmp/agent-capsule-phase6-traces.json
)

run_id="$(
  python3 - <<'PY'
import json
with open("/tmp/agent-capsule-phase6-traces.json", "r", encoding="utf-8") as handle:
    print(json.load(handle)["traces"][0]["run_id"])
PY
)"

(
  cd "$tmp_dir"
  python3 -m agent_capsule_cli trace export --safe "$run_id" --output "$safe_trace_path" --json >/tmp/agent-capsule-phase6-export.json
)

PYTHONPATH=ci python3 "$repo_root/ci/validate-json-file.py" \
  "$repo_root/schemas/safe-trace.schema.json" \
  "$safe_trace_path"

SAFE_TRACE_PATH="$safe_trace_path" python3 - <<'PY'
import json
import os
from pathlib import Path

from agent_capsule.safe_trace import scan_safe_trace

safe_trace = json.loads(Path(os.environ["SAFE_TRACE_PATH"]).read_text(encoding="utf-8"))
raw_values = [
    "claimant@example.com",
    "Neck pain reported after accident",
    "Rear-end collision at low speed",
    "Claim requires review because medical context is present",
]
findings = scan_safe_trace(safe_trace, raw_values)
if findings:
    raise SystemExit("safe trace scanner findings: %s" % "; ".join(findings))
PY

for output_file in \
  /tmp/agent-capsule-phase6-run.txt \
  /tmp/agent-capsule-phase6-traces.json \
  /tmp/agent-capsule-phase6-export.json \
  "$safe_trace_path"
do
  for raw_value in \
    "claimant@example.com" \
    "Neck pain reported after accident" \
    "Rear-end collision at low speed" \
    "Claim requires review because medical context is present"
  do
    if grep -q "$raw_value" "$output_file"; then
      echo "Safe trace export leaked raw payload value in $output_file: $raw_value" >&2
      exit 1
    fi
  done
done

echo "Phase 6 safe trace export checks passed."

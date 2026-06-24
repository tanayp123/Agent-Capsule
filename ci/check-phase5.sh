#!/usr/bin/env bash
set -euo pipefail

bash ci/check-phase4.sh
source ci/python-env.sh
export PYTHONPATH="$PWD/cli/src:$PYTHONPATH"

python3 -m unittest discover -s policy-engine/tests -p 'test_*.py'
python3 -m unittest cli/tests/test_cli.py
python3 -m unittest sdk-python/tests/test_observe.py

python3 - <<'PY'
import json
import sys
from pathlib import Path

from policy_engine import generate_privacy_map, load_policy_file, load_trace_file

root = Path.cwd()
policy = load_policy_file(root / "fixtures/policies/restrictive-policy.json")
trace = load_trace_file(root / "fixtures/traces/crm-privacy-review.json")
actual = generate_privacy_map(trace, policy)
expected = json.loads((root / "fixtures/privacy-maps/crm-journey-privacy-map.json").read_text(encoding="utf-8"))

if actual != expected:
    print("CRM privacy-map fixture drifted.", file=sys.stderr)
    print(json.dumps(actual, indent=2, sort_keys=True), file=sys.stderr)
    sys.exit(1)
PY

set +e
python3 -m agent_capsule_cli policy check \
  --policy fixtures/policies/restrictive-policy.json \
  --trace fixtures/traces/crm-privacy-review.json \
  --fail-on high-risk-egress \
  --json >/tmp/agent-capsule-phase5-policy-gate.json
policy_gate_status="$?"
set -e

if [ "$policy_gate_status" -eq 0 ]; then
  echo "Expected policy gate to fail on undeclared high-risk egress" >&2
  exit 1
fi

python3 - <<'PY'
import json

with open("/tmp/agent-capsule-phase5-policy-gate.json", "r", encoding="utf-8") as handle:
    output = json.load(handle)

assert output["ok"] is False
assert any(finding["kind"] == "undeclared_high_risk_egress" for finding in output["findings"])
assert {item["action"] for item in output["policy_suggestions"]} == {
    "allow",
    "allow_fields",
    "redact",
    "require_approval",
    "block",
}
PY

if grep -q "claimant@example.com" /tmp/agent-capsule-phase5-policy-gate.json; then
  echo "Policy gate output leaked raw payload value" >&2
  exit 1
fi

echo "Phase 5 policy engine and privacy-map checks passed."

#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

bash ci/check-phase13.sh
source ci/python-env.sh
export PYTHONPATH="$repo_root/cli/src:$PYTHONPATH"

python3 -m unittest cli/tests/test_cli.py

tmp_dir="${TMPDIR:-/tmp}/agent-capsule-phase14-demo"
rm -rf "$tmp_dir"
mkdir -p "$tmp_dir"

cat >"$tmp_dir/requirements.txt" <<'REQ'
agent-capsule==0.1.0
REQ

python3 -m agent_capsule_cli build \
  --source-dir "$tmp_dir" \
  --policy fixtures/policies/crm-policy.json \
  --output "$tmp_dir/capsule-manifest.json" \
  --build-report "$tmp_dir/build-report.json" \
  --runtime-version 3.10.14 \
  --model-provider "Example Model" \
  --model example-large \
  --required-secret MODEL_PROVIDER_API_KEY \
  --required-secret CRM_API_KEY \
  --signing-key phase14-demo-signing-key \
  --key-id phase14-demo-key \
  --json >"$tmp_dir/build-output.json"

python3 -m agent_capsule_cli demo create \
  --customer acme-insurance \
  --mode confidential \
  --manifest "$tmp_dir/capsule-manifest.json" \
  --policy fixtures/policies/crm-policy.json \
  --trace fixtures/traces/tool-call-sensitive-payload.json \
  --secret MODEL_PROVIDER_API_KEY \
  --secret CRM_API_KEY \
  --output-dir "$tmp_dir/demos" \
  --json >"$tmp_dir/demo-success.json"

python3 - "$tmp_dir/demo-success.json" <<'PY'
import json
import sys
from pathlib import Path

result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert result["ok"] is True
assert result["attestation"]["verified"] is True
assert result["secret_release"]["released"] is True
assert Path(result["verification_page"]).exists()
assert Path(result["vendor_telemetry"]).exists()
PY

cat >"$tmp_dir/failed-attestation.json" <<'JSON'
{
  "provider": "local-confidential-like",
  "status": "failed",
  "reason": "measurement mismatch"
}
JSON

set +e
python3 -m agent_capsule_cli demo create \
  --customer acme-insurance \
  --mode confidential \
  --manifest "$tmp_dir/capsule-manifest.json" \
  --policy fixtures/policies/crm-policy.json \
  --secret MODEL_PROVIDER_API_KEY \
  --secret CRM_API_KEY \
  --attestation-evidence "$tmp_dir/failed-attestation.json" \
  --output-dir "$tmp_dir/demos-failed-attestation" \
  --json >"$tmp_dir/demo-attestation-fail.json"
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  echo "Demo unexpectedly passed failed attestation" >&2
  exit 1
fi

set +e
python3 -m agent_capsule_cli demo create \
  --customer acme-insurance \
  --mode confidential \
  --manifest "$tmp_dir/capsule-manifest.json" \
  --policy fixtures/policies/crm-policy.json \
  --output-dir "$tmp_dir/demos-missing-secrets" \
  --json >"$tmp_dir/demo-missing-secrets.json"
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  echo "Demo unexpectedly passed with missing secrets" >&2
  exit 1
fi

python3 -m agent_capsule_cli build \
  --source-dir "$tmp_dir" \
  --policy fixtures/policies/restrictive-policy.json \
  --output "$tmp_dir/restrictive-manifest.json" \
  --build-report "$tmp_dir/restrictive-report.json" \
  --runtime-version 3.10.14 \
  --signing-key phase14-demo-signing-key \
  --key-id phase14-demo-key \
  --json >"$tmp_dir/restrictive-build-output.json"

set +e
python3 -m agent_capsule_cli demo create \
  --customer acme-insurance \
  --mode confidential \
  --manifest "$tmp_dir/restrictive-manifest.json" \
  --policy fixtures/policies/restrictive-policy.json \
  --trace fixtures/traces/crm-privacy-review.json \
  --output-dir "$tmp_dir/demos-policy-fail" \
  --json >"$tmp_dir/demo-policy-fail.json"
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  echo "Demo unexpectedly passed undeclared high-risk egress" >&2
  exit 1
fi

python3 - "$tmp_dir/demo-attestation-fail.json" "$tmp_dir/demo-missing-secrets.json" "$tmp_dir/demo-policy-fail.json" <<'PY'
import json
import sys
from pathlib import Path

expected = [
    ("attestation_failed", Path(sys.argv[1])),
    ("missing_required_secrets", Path(sys.argv[2])),
    ("undeclared_high_risk_egress", Path(sys.argv[3])),
]
for code, path in expected:
    result = json.loads(path.read_text(encoding="utf-8"))
    codes = {finding["code"] for finding in result["findings"]}
    assert code in codes, (code, codes)
    assert result["support_bundle"]
    assert Path(result["support_bundle"]).exists()
PY

signature_value="$(python3 - "$tmp_dir/capsule-manifest.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["signature"]["value"])
PY
)"

if grep -R -q "claimant@example.com\|Sensitive account note\|$signature_value" "$tmp_dir"/demo*.json "$tmp_dir"/demos*; then
  echo "Confidential demo artifacts leaked plaintext payload or signature value" >&2
  exit 1
fi

echo "Phase 14 confidential demo checks passed."

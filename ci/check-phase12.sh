#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

bash ci/check-phase11.sh
source ci/python-env.sh
export PYTHONPATH="$repo_root/cli/src:$PYTHONPATH"

python3 -m unittest cli/tests/test_cli.py

tmp_dir="${TMPDIR:-/tmp}/agent-capsule-phase12-ci"
rm -rf "$tmp_dir"
mkdir -p "$tmp_dir/metadata"

python3 -m agent_capsule_cli ci check \
  --policy fixtures/policies/crm-policy.json \
  --trace fixtures/traces/failed-model-call.json \
  --trace fixtures/traces/tool-call-sensitive-payload.json \
  --manifest fixtures/manifests/signed-manifest.json \
  --release \
  --json >"$tmp_dir/pass.json"

python3 - "$tmp_dir/pass.json" <<'PY'
import json
import sys
from pathlib import Path

result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert result["ok"] is True
assert result["summary"]["error_count"] == 0
assert result["annotations"] == []
PY

set +e
python3 -m agent_capsule_cli ci check \
  --policy fixtures/policies/restrictive-policy.json \
  --trace fixtures/traces/crm-privacy-review.json \
  --release \
  --json >"$tmp_dir/fail.json"
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  echo "CI privacy gate unexpectedly passed" >&2
  exit 1
fi

python3 - "$tmp_dir/fail.json" <<'PY'
import json
import sys
from pathlib import Path

result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
codes = {finding["code"] for finding in result["findings"]}
required = {
    "undeclared_destination",
    "undeclared_high_risk_egress",
    "high_risk_unapproved_destination",
    "manifest_required",
}
missing = required - codes
assert result["ok"] is False
assert not missing, sorted(missing)
assert result["annotations"]
PY

cp fixtures/traces/failed-model-call.json "$tmp_dir/metadata/failed-model-call.json"
python3 -m agent_capsule_cli ci check \
  --policy fixtures/policies/crm-policy.json \
  --trace-dir "$tmp_dir" \
  --manifest fixtures/manifests/signed-manifest.json \
  --release \
  --json >"$tmp_dir/trace-dir-pass.json"

python3 - "$tmp_dir/trace-dir-pass.json" <<'PY'
import json
import sys
from pathlib import Path

result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert result["ok"] is True
assert result["summary"]["trace_count"] == 1
PY

if grep -q "claimant@example.com\|sig_test_value" "$tmp_dir/pass.json" "$tmp_dir/fail.json" "$tmp_dir/trace-dir-pass.json"; then
  echo "CI check output leaked payload or signature material" >&2
  exit 1
fi

echo "Phase 12 CI/CD integration checks passed."

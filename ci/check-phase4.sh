#!/usr/bin/env bash
set -euo pipefail

bash ci/check-phase3.sh
source ci/python-env.sh
export PYTHONPATH="$PWD/cli/src:$PYTHONPATH"
python3 -m unittest cli/tests/test_cli.py

repo_root="$PWD"
tmp_dir="${TMPDIR:-/tmp}/agent-capsule-phase4-cli"
rm -rf "$tmp_dir"
mkdir -p "$tmp_dir"

(
  cd "$tmp_dir"
  python3 -m agent_capsule_cli init --json >/tmp/agent-capsule-phase4-init.json
  python3 -m agent_capsule_cli policy check --json >/tmp/agent-capsule-phase4-policy.json
  python3 -m agent_capsule_cli run --mode observe -- python3 "$repo_root/examples/claims-triage-python/claims_triage.py" >/tmp/agent-capsule-phase4-run.txt
  python3 -m agent_capsule_cli trace list --json >/tmp/agent-capsule-phase4-traces.json
  python3 -m agent_capsule_cli manifest inspect "$repo_root/fixtures/manifests/signed-manifest.json" --json >/tmp/agent-capsule-phase4-manifest.json
)

python3 - <<'PY'
import json
for path in [
    "/tmp/agent-capsule-phase4-init.json",
    "/tmp/agent-capsule-phase4-policy.json",
    "/tmp/agent-capsule-phase4-traces.json",
    "/tmp/agent-capsule-phase4-manifest.json",
]:
    with open(path, "r", encoding="utf-8") as handle:
        json.load(handle)
PY

for output_file in \
  /tmp/agent-capsule-phase4-init.json \
  /tmp/agent-capsule-phase4-policy.json \
  /tmp/agent-capsule-phase4-run.txt \
  /tmp/agent-capsule-phase4-traces.json \
  /tmp/agent-capsule-phase4-manifest.json
do
  if grep -q "claimant@example.com" "$output_file"; then
    echo "CLI output leaked raw payload value in $output_file" >&2
    exit 1
  fi
  if grep -q "sig_test_value" "$output_file"; then
    echo "CLI output leaked raw manifest signature in $output_file" >&2
    exit 1
  fi
done

echo "Phase 4 CLI MVP checks passed."

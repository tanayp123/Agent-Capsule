#!/usr/bin/env bash
set -euo pipefail

bash ci/check-phase6.sh
source ci/python-env.sh
export PYTHONPATH="$PWD/cli/src:$PYTHONPATH"

python3 -m unittest sdk-python/tests/test_replay.py
python3 -m unittest cli/tests/test_cli.py

python3 - <<'PY'
import json
from pathlib import Path

for path in sorted(Path("fixtures/replays").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))
PY

repo_root="$PWD"
tmp_dir="${TMPDIR:-/tmp}/agent-capsule-phase7-replay"
rm -rf "$tmp_dir"
mkdir -p "$tmp_dir"

(
  cd "$tmp_dir"
  python3 -m agent_capsule_cli init --json >/tmp/agent-capsule-phase7-init.json
  python3 -m agent_capsule_cli run --mode observe -- python3 "$repo_root/examples/claims-triage-python/claims_triage.py" >/tmp/agent-capsule-phase7-run.txt
  python3 -m agent_capsule_cli trace list --json >/tmp/agent-capsule-phase7-traces.json
)

run_id="$(
  python3 - <<'PY'
import json
with open("/tmp/agent-capsule-phase7-traces.json", "r", encoding="utf-8") as handle:
    print(json.load(handle)["traces"][0]["run_id"])
PY
)"

(
  cd "$tmp_dir"
  python3 -m agent_capsule_cli trace replay "$run_id" --mode structural --output structural-replay.json --json >/tmp/agent-capsule-phase7-structural.json
  python3 -m agent_capsule_cli trace replay "$run_id" --mode mocked --output mocked-replay.json --json >/tmp/agent-capsule-phase7-mocked.json
  python3 -m agent_capsule_cli trace replay "$run_id" --mode redacted --output redacted-replay.json --json >/tmp/agent-capsule-phase7-redacted.json
  python3 -m agent_capsule_cli trace replay "$run_id" --mode approved_plaintext --approve-plaintext --output approved-replay.json --json >/tmp/agent-capsule-phase7-approved.json
  python3 -m agent_capsule_cli trace replay "$run_id" --compare mocked-replay.json --output comparison.json --json >/tmp/agent-capsule-phase7-comparison.json
)

set +e
(
  cd "$tmp_dir"
  python3 -m agent_capsule_cli trace replay "$run_id" --mode approved_plaintext --json >/tmp/agent-capsule-phase7-unapproved.json
)
unapproved_status="$?"
set -e

if [ "$unapproved_status" -eq 0 ]; then
  echo "Expected approved_plaintext replay without approval to fail" >&2
  exit 1
fi

TMP_REPLAY_DIR="$tmp_dir" python3 - <<'PY'
import json
import os
from pathlib import Path

from agent_capsule.safe_trace import scan_safe_trace

tmp_dir = Path(os.environ["TMP_REPLAY_DIR"])
for path in [
    tmp_dir / "structural-replay.json",
    tmp_dir / "mocked-replay.json",
    tmp_dir / "redacted-replay.json",
    tmp_dir / "approved-replay.json",
]:
    replay = json.loads(path.read_text(encoding="utf-8"))
    assert replay["payload_policy"]["raw_payloads_exported"] is False
    findings = scan_safe_trace(replay, [
        "claimant@example.com",
        "Neck pain reported after accident",
        "Rear-end collision at low speed",
        "Claim requires review because medical context is present",
    ])
    if findings:
        raise SystemExit("%s scanner findings: %s" % (path, "; ".join(findings)))

comparison = json.loads((tmp_dir / "comparison.json").read_text(encoding="utf-8"))
assert comparison["status"] == "match"
PY

for output_file in \
  /tmp/agent-capsule-phase7-run.txt \
  /tmp/agent-capsule-phase7-traces.json \
  /tmp/agent-capsule-phase7-structural.json \
  /tmp/agent-capsule-phase7-mocked.json \
  /tmp/agent-capsule-phase7-redacted.json \
  /tmp/agent-capsule-phase7-approved.json \
  /tmp/agent-capsule-phase7-comparison.json \
  "$tmp_dir/structural-replay.json" \
  "$tmp_dir/mocked-replay.json" \
  "$tmp_dir/redacted-replay.json" \
  "$tmp_dir/approved-replay.json" \
  "$tmp_dir/comparison.json"
do
  for raw_value in \
    "claimant@example.com" \
    "Neck pain reported after accident" \
    "Rear-end collision at low speed" \
    "Claim requires review because medical context is present"
  do
    if grep -q "$raw_value" "$output_file"; then
      echo "Replay output leaked raw payload value in $output_file: $raw_value" >&2
      exit 1
    fi
  done
done

echo "Phase 7 replay checks passed."

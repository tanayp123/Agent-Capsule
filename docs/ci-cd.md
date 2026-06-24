# CI/CD Pull Request Workflow

Agent Capsule CI/CD integration turns privacy behavior into a pull request gate. The gate reads policy files, safe trace metadata, and optional capsule manifests. It does not decrypt trace payload sidecars and does not print prompt content, document text, model outputs, tool payloads, secrets, user identifiers, or manifest signature values.

## Command

Run from the repository root:

```bash
source ci/python-env.sh
export PYTHONPATH="$PWD/cli/src:$PYTHONPATH"
python3 -m agent_capsule_cli ci check \
  --policy agent-capsule.policy.yaml \
  --trace-dir .agent-capsule/traces \
  --manifest .agent-capsule/manifests/capsule-manifest.json \
  --release \
  --annotation-format github \
  --json
```

Use `--trace path/to/trace.json` one or more times when CI collects explicit trace artifacts instead of a trace store directory.

## Merge-Blocking Conditions

`capsule ci check` exits with code `1` when any error finding is present:

- `policy_missing`: the policy file cannot be found.
- `policy_malformed`: the policy file cannot be parsed or fails policy validation.
- `policy_version_too_old`: the policy version is lower than `--min-policy-version`.
- `trace_missing`: a requested trace metadata file cannot be found.
- `trace_malformed`: a requested trace metadata file is not valid JSON.
- `undeclared_destination`: a destination appears in trace metadata but is not declared in policy.
- `undeclared_high_risk_egress`: high-risk egress remains for an undeclared destination.
- `high_risk_unapproved_destination`: high-risk data classes reach a destination without an approved policy action.
- `manifest_required`: `--release` was used without a manifest.
- `manifest_missing`: the requested manifest file cannot be found.
- `manifest_malformed`: the manifest is not valid JSON.
- `manifest_invalid`: the manifest does not satisfy required manifest fields.
- `manifest_signature_missing`: release builds do not include a manifest signature value.
- `runtime_unsupported`: release builds use an unsupported or unknown runtime version.

Approved policy actions for high-risk data are `allow`, `allow_fields`, `redact`, and `require_approval` on a declared destination. A blocked, warning, missing, or unevaluated policy path remains a CI failure until the policy is updated or the egress is removed.

## JSON Report

With `--json`, the command writes:

- `ok`: boolean pass/fail result.
- `summary`: counts and CI format metadata.
- `findings`: safe machine-readable findings.
- `annotations`: generic annotation objects labeled for `json`, `github`, `gitlab`, or `buildkite`.
- `privacy_maps`: safe data-flow summaries for evaluated traces.

The annotation objects include file path, line number placeholder, severity, title, message, destination id, risk, data classes, and trace id. They are safe to upload as CI artifacts.

## Platform Examples

Copy-paste examples are available in:

- `ci/examples/github-actions-agent-capsule.yml`
- `ci/examples/gitlab-ci-agent-capsule.yml`
- `ci/examples/buildkite-agent-capsule.yml`

Each example runs `capsule ci check`, preserves `agent-capsule-ci.json` as a CI artifact, and uses the CLI exit code to block merge when privacy or release evidence fails.

## Local Verification

Run the full Phase 12 check:

```bash
bash ci/check-phase12.sh
```

The script verifies a passing release gate, verifies a failing privacy drift gate, checks trace-directory discovery, and scans CI output for known payload and signature strings.

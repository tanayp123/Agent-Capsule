# Phase 12 Review: CI/CD Integration

## Scope Reviewed

- Added `capsule ci check` for pull request privacy and release gates.
- Added JSON findings and annotation output for CI systems.
- Added GitHub Actions, GitLab CI, and Buildkite examples.
- Added Phase 12 integration script and documentation.

## Exit Codes

- Exit code `0`: no error findings are present.
- Exit code `1`: one or more error findings are present, including privacy drift, malformed policy, stale policy version, missing release manifest, missing signature, or unsupported runtime version.
- Exit code `130`: inherited keyboard interrupt behavior from the CLI.

## Payload Leakage Review

The CI command reads safe trace metadata and policy/manifest metadata only. It does not decrypt trace payload sidecars. Text output and JSON findings include destination ids, risk levels, data class names, trace ids, and file paths. They do not include raw prompts, document text, model outputs, tool payloads, secrets, user identifiers, or manifest signature values.

`ci/check-phase12.sh` scans generated CI JSON for known fixture payload and signature strings.

## Copy-Paste Review

The examples in `ci/examples/` use the same command shape:

```bash
python3 -m agent_capsule_cli ci check \
  --policy agent-capsule.policy.yaml \
  --trace-dir .agent-capsule/traces \
  --manifest .agent-capsule/manifests/capsule-manifest.json \
  --release \
  --json
```

Each example preserves `agent-capsule-ci.json` as a build artifact and relies on the CLI exit code to block merge.

## Verification

Run:

```bash
bash ci/check-phase12.sh
```

This runs previous phase checks, CLI unit tests, a passing release gate, a failing privacy drift gate, trace-directory discovery, and output leakage checks.

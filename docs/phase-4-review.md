# Phase 4 Review

Status: Complete

Review date: 2026-06-23

## Review Scope

Phase 4 establishes:

- CLI package structure
- `capsule init`
- `capsule run --mode observe -- <command>`
- `capsule trace list`
- `capsule policy check`
- `capsule manifest inspect`
- JSON output support
- Local config creation
- Local trace-store key creation
- CLI unit and integration tests

## Review Checklist

- Developer can initialize a local Agent Capsule workspace.
- Developer can run an instrumented command in Observe mode.
- Developer can list safe trace metadata.
- Policy check returns clear success or failure for generated YAML and JSON fixtures.
- Manifest inspect shows safe metadata without signature values.
- CLI output does not print raw sample payload values.
- Malformed config returns a clean error without traceback.
- `capsule run` suppresses child command output by default.

## Findings

Findings:

- No blocking findings.
- `bash ci/check-phase4.sh` passes.
- CLI integration tests cover init, run, trace list, policy check, manifest inspect, and malformed config behavior.
- During review, subprocess import failed when tests changed directories because `PYTHONPATH` used relative paths. `ci/python-env.sh` now exports absolute SDK paths and `check-phase4.sh` exports an absolute CLI path.
- During review, `capsule run` was updated to suppress child stdout and stderr by default to avoid relaying raw payloads.

Known follow-up for Phase 5:

- Replace policy shape checks with the full policy engine.
- Add undeclared destination detection.
- Add high-risk egress failure behavior.
- Generate policy suggestions from observed traces.


# Phase 5 Review

## Scope Reviewed

- Policy parser and validation behavior for JSON policies and generated YAML policies.
- Decision precedence for secrets, undeclared high-risk egress, undeclared destinations, approval, redaction, field allowlists, and allow.
- Privacy-map generation from trace metadata.
- `capsule policy check --fail-on high-risk-egress` exit behavior.
- SDK trace policy decisions with a loaded policy.

## Findings Fixed

- Replaced the Phase 1 duplicate policy evaluator with the Phase 5 engine for conformance checks.
- Added deterministic output ordering for policy decisions, privacy-map findings, and developer suggestions.
- Avoided test pollution from mutable destination objects by using fresh destination instances where policy evaluation mutates trace metadata.
- Added a YAML parser regression test for destination allow, redact, and approval lists.

## Residual Risks

- YAML support is intentionally limited to the simple policy shape generated and documented by Agent Capsule.
- Field-to-data-class matching uses trace metadata data classes in the MVP; raw field-name mapping remains future work for richer SDK instrumentation.

## Verification

```bash
bash ci/check-phase5.sh
```

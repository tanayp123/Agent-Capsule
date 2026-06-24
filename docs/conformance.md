# Conformance Fixtures

Conformance fixtures define behavior every SDK must match.

## Fixture Groups

- `fixtures/traces/`: trace examples and edge cases.
- `fixtures/policies/`: policy documents used by CLI and SDK tests.
- `fixtures/manifests/`: signed manifest examples.
- `fixtures/safe-traces/`: safe trace examples.
- `fixtures/conformance/`: deterministic expected outcomes.

## SDK Requirements

Every SDK must:

- Produce trace documents compatible with `schemas/trace.schema.json`.
- Produce destination records compatible with `schemas/destination.schema.json`.
- Apply policy semantics from `docs/policy-semantics.md`.
- Produce safe traces compatible with `schemas/safe-trace.schema.json`.
- Produce or consume manifests compatible with `schemas/manifest.schema.json`.
- Pass policy decision cases in `fixtures/conformance/policy-decisions.json`.

## Phase 1 Validator

The Phase 1 validator is intentionally dependency-free so it can run before package tooling exists.

Run:

```bash
bash ci/check-phase1.sh
```

Later phases may add a full JSON Schema validator, but the conformance fixture semantics must remain stable.


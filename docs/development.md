# Local Development

This document describes how to work on Agent Capsule during the foundation phase.

## Source Of Truth

- Product requirements: `PRD.md`
- Implementation plan: `agent.md`
- Phase 0 review record: `docs/phase-0-review.md`

## Repository Setup

The current foundation and schema checks do not require package installation. The repository can be validated with:

```bash
bash ci/check-foundation.sh
bash ci/check-phase1.sh
bash ci/check-phase2.sh
bash ci/check-phase3.sh
bash ci/check-phase4.sh
bash ci/check-phase5.sh
bash ci/check-phase6.sh
bash ci/check-phase7.sh
bash ci/check-phase8.sh
bash ci/check-phase9.sh
bash ci/check-phase10.sh
bash ci/check-phase11.sh
bash ci/check-phase12.sh
bash ci/check-phase13.sh
bash ci/check-phase14.sh
bash ci/check-phase15.sh
```

## Development Sequence

1. Read `PRD.md`.
2. Read `agent.md`.
3. Confirm the active implementation phase.
4. Update only the codebase or docs owned by that phase.
5. Add or update tests for any behavior change.
6. Run the relevant checks.
7. Complete the phase review and fix findings before continuing.

## Codebase Boundaries

- `cli/`: command-line entrypoint.
- `sdk-python/`: first SDK wedge.
- `policy-engine/`: deterministic policy semantics and tests.
- `trace-store/`: encrypted local trace storage.
- `local-api/`: localhost-only API bridge for the console.
- `agent-capsule-console/`: developer console for encrypted traces and data-flow visibility.
- `agent-capsule-website/`: separate product website.
- `schemas/`: shared schemas.
- `fixtures/`: shared conformance fixtures.

## Phase 0 Check

Run:

```bash
bash ci/check-foundation.sh
```

This check validates the initial repository structure and documentation. Phase 1 adds schema, fixture, policy conformance, and safe trace scanner checks. Phase 2 adds Python SDK observe-mode tests and sample trace validation. Phase 3 adds encrypted trace-store tests. Phase 4 adds CLI tests and integration checks. Phase 5 adds policy-engine, privacy-map, and high-risk egress gate checks. Phase 6 adds safe trace export and plaintext scanner checks. Phase 7 adds replay and replay-comparison checks. Phase 8 adds console build and browser checks. Phase 9 adds localhost API bridge checks. Phase 10 adds Guard Mode enforcement checks. Phase 11 adds capsule build and signed manifest checks. Phase 12 adds pull request CI/CD privacy and release evidence checks. Phase 13 adds TypeScript, Java, Go, and Rust SDK beta checks. Phase 14 adds confidential demo startup, attestation, secret release, customer verification, safe telemetry, and support bundle checks. Phase 15 adds product website build, browser, copy, and visual-rule checks. Later phases will harden enterprise deployment workflows.

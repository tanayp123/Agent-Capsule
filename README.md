# Agent Capsule

Agent Capsule is a private agent SDK, CLI, console, and deployment workflow for debugging and packaging AI agents without exposing sensitive prompts, documents, model outputs, tool payloads, secrets, or user identifiers by default.

## Current Phase

Phase 15: Product Website.

This repository currently contains:

- `PRD.md`: product requirements and scope.
- `agent.md`: implementation plan and phase gates.
- `docs/`: foundation documentation for development, tooling, security, hardware, coding standards, and terminology.
- `ci/`: local CI checks for repository foundation, schemas, fixtures, and policy conformance.
- Implemented Python SDK, encrypted trace store, CLI, policy engine, local API bridge, Agent Capsule Console, schemas, fixtures, CI checks, and the claims-triage sample.
- Placeholder directories remain for future SDKs, website hardening, and later implementation phases.

## Showcase Demo

The fastest way to show the product is the Agent Capsule Console guided demo:

1. Start the console in `agent-capsule-console`.
2. Run the claims-triage sample in Observe mode.
3. Launch `capsule view` to connect the localhost bridge.
4. Click `Run live agent test`.
5. Review where data went and export safe evidence.

Detailed commands are in `agent-capsule-console/README.md`.

The current demo product position is: private agent observability for enterprise AI teams. It combines encrypted traces, data-flow visibility, policy findings, and share-safe evidence so teams can debug and sell agents without handing over plaintext customer data.

## Phase Status

Phase 0 established structure, ownership, and guardrails.

Phase 1 added shared schemas, conformance fixtures, policy semantics, hashing and redaction rules, safe trace retention rules, and validation checks.

Phase 2 adds the Python SDK observe-mode slice, including run/span contexts, model and tool wrappers, structured field classification, schema-compatible trace output, tests, and a claims-triage sample.

Phase 3 adds local encrypted payload sidecars, separate safe metadata files, trace listing, run lookup, deletion, retention, migration hooks, and corrupted payload handling.

Phase 4 adds the CLI MVP for initialization, observe-mode subprocess execution, safe trace listing, policy shape checks, and manifest metadata inspection.

Phase 5 adds deterministic policy evaluation, data-flow privacy-map generation, undeclared destination detection, policy suggestions, and a CI gate for undeclared high-risk egress.

Phase 6 adds safe trace export, plaintext scanning, CLI export support, and a console import fixture for team debugging without raw payload exposure.

Phase 7 adds structural replay, mocked replay, redacted payload replay, approved local plaintext verification, replay comparison, fixtures, and CLI replay support.

Phase 8 adds the Next.js, TypeScript, Tailwind, and shadcn/ui Agent Capsule Console with safe metadata views, local API client wiring, session token handling, reveal confirmation, and browser tests.

Phase 9 adds the localhost-only local API bridge, `capsule view` bridge startup, ephemeral session-token auth, safe metadata endpoints, audited local payload reveal controls, and console shutdown signaling.

Phase 10 adds Guard Mode enforcement for supported Python model and tool wrappers, including fail-closed policy loading, pre-egress policy checks, redaction, allow-fields filtering, blocking, warnings, human approval hooks, and deterministic trace decisions.

Phase 11 adds `capsule build` for signed capsule manifests, dependency lockfile hashes, prompt template hashes without plaintext, tool schema hashes, model configuration evidence, network destinations, required secrets, build reports, and stricter safe manifest inspection.

Phase 12 adds `capsule ci check`, CI annotation JSON, pull request gates for undeclared high-risk egress, undeclared destinations, high-risk data reaching unapproved destinations, malformed or stale policy files, release manifest signature checks, release runtime checks, and GitHub Actions, GitLab CI, and Buildkite examples.

Phase 13 adds beta TypeScript, Java, Go, and Rust SDK surfaces with shared policy semantics, field classification, wrappers/interceptors, context propagation patterns, conformance tests, and cross-language trace fixtures.

Phase 14 adds `capsule demo create` for confidential customer proof-of-concept flows, including signed manifest enforcement, policy privacy gates, confidential-like local environment startup, attestation capture, secret release receipts, customer verification pages, safe vendor telemetry, and sanitized support bundles.

Phase 15 adds the separate Next.js, TypeScript, Tailwind CSS, and shadcn/ui-style product website with enterprise-oriented US English copy, product evidence visuals, privacy review, safe trace collaboration, confidential demo, multi-language SDK, hardware requirements, and enterprise evidence sections.

Run the foundation check:

```bash
bash ci/check-foundation.sh
```

Run the Phase 1 schema and conformance check:

```bash
bash ci/check-phase1.sh
```

Run the Phase 2 Python observe-mode check:

```bash
bash ci/check-phase2.sh
```

Run the Phase 3 encrypted trace-store check:

```bash
bash ci/check-phase3.sh
```

Run the Phase 4 CLI MVP check:

```bash
bash ci/check-phase4.sh
```

Run the Phase 5 policy engine and privacy-map check:

```bash
bash ci/check-phase5.sh
```

Run the Phase 6 safe trace export check:

```bash
bash ci/check-phase6.sh
```

Run the Phase 7 replay check:

```bash
bash ci/check-phase7.sh
```

Run the Phase 8 console check:

```bash
bash ci/check-phase8.sh
```

Run the Phase 9 local API bridge check:

```bash
bash ci/check-phase9.sh
```

Run the Phase 10 Guard Mode check:

```bash
bash ci/check-phase10.sh
```

Run the Phase 11 capsule build check:

```bash
bash ci/check-phase11.sh
```

Run the Phase 12 CI/CD integration check:

```bash
bash ci/check-phase12.sh
```

Run the Phase 13 multi-language SDK beta check:

```bash
bash ci/check-phase13.sh
```

Run the Phase 14 confidential demo check:

```bash
bash ci/check-phase14.sh
```

Run the Phase 15 product website check:

```bash
bash ci/check-phase15.sh
```

## Privacy Baseline

Raw prompts, documents, model outputs, tool payloads, secrets, and user identifiers must remain local by default. CI and developer tooling must not print raw trace payloads.

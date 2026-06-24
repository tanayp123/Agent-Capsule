# Agent Capsule Implementation Plan

Source document: `PRD.md`  
Objective: implement Agent Capsule end to end, including SDKs, CLI, trace storage, policy checks, safe traces, replay, console UI, product website, confidential demo path, tests, documentation, code review, and bug fixing.

## 1. Operating Rules For The Implementation Agent

The implementation agent must:

- Treat `PRD.md` as the source of truth.
- Keep raw prompts, documents, model outputs, tool payloads, secrets, and user identifiers local by default.
- Prefer a working vertical slice before expanding breadth.
- Keep Python as the first SDK wedge.
- Design shared schemas and policy semantics before adding additional language SDKs.
- Maintain separate codebases for SDK/CLI, Agent Capsule Console, and the product website.
- Run tests, linters, type checks, and build checks before completing each phase.
- Perform a code review after each phase.
- Fix review findings and bugs before starting the next phase.
- Document setup, run, test, and release steps as implementation lands.

## 2. Target Repository Layout

Recommended repository structure:

```text
agent-capsule/
  PRD.md
  agent.md
  schemas/
    trace.schema.json
    policy.schema.json
    manifest.schema.json
    safe-trace.schema.json
  fixtures/
    traces/
    policies/
    manifests/
    safe-traces/
  cli/
  sdk-python/
  sdk-typescript/
  sdk-java/
  sdk-go/
  sdk-rust/
  policy-engine/
  trace-store/
  local-api/
  agent-capsule-console/
  agent-capsule-website/
  examples/
    claims-triage-python/
  docs/
  ci/
```

The exact layout may change if the implementation language or package manager requires it, but ownership boundaries must stay clear.

## 3. Global Definition Of Done

The product is end-to-end complete when:

- A developer can install the Python SDK and trace an existing Python agent.
- Local traces are encrypted at rest.
- Trace metadata can be viewed without exposing plaintext payloads.
- The privacy map detects undeclared destinations.
- Policy actions support allow, allow selected fields, redact, require approval, warn, and block.
- `capsule policy check` fails CI when undeclared high-risk egress remains.
- A safe trace can be exported with no plaintext sensitive payloads.
- Replay can run with mocked, redacted, or approved local payloads.
- `capsule build` creates a signed capsule manifest.
- Agent Capsule Console displays runs, timelines, data-flow visibility, privacy maps, policy decisions, safe trace export, replay comparison, and manifest inspection.
- TypeScript, Java, Go, and Rust SDKs pass shared conformance tests before beta.
- Confidential demo flow can create a verified private proof of concept with safe vendor observability.
- Product website requirements are implemented as a separate Next.js and shadcn/ui codebase when website implementation begins.
- Documentation explains hardware requirements, setup, usage, testing, and deployment.
- All phases have passed code review and bug-fix gates.

## 4. Phase 0: Product And Engineering Foundation

Goal: turn the PRD into an executable engineering foundation.

Tasks:

- Create the repository structure.
- Select package managers and build tooling for each codebase.
- Define coding standards for Python, TypeScript, Java, Go, and Rust.
- Define shared terminology: run, trace, span, destination, data class, policy decision, safe trace, manifest, capsule.
- Create initial docs for local development.
- Add CI skeleton for lint, type check, unit tests, schema validation, and build checks.
- Add security baseline: no secrets in logs, no plaintext trace payloads in CI output, no remote sync by default.
- Document hardware requirements:
  - No specialized local hardware required for SDK, CLI, console, safe traces, replay, or policy checks.
  - GPU only required if the user's own agent runs local models.
  - Confidential mode requires supported cloud confidential-computing infrastructure.

Review and bug-fix gate:

- Review repository layout against `PRD.md`.
- Verify every codebase has a clear owner and README placeholder.
- Fix missing CI jobs, unclear setup instructions, or naming drift before continuing.

Exit criteria:

- The repo can run a no-op CI pipeline.
- Development setup is documented.
- Hardware assumptions are documented.

## 5. Phase 1: Shared Schemas And Conformance Fixtures

Goal: define stable cross-language artifacts before building SDK breadth.

Tasks:

- Implement JSON schemas for:
  - Trace event
  - Destination
  - Policy
  - Safe trace
  - Capsule manifest
- Define semantic rules for policy evaluation.
- Define data classes and risk levels.
- Define hashing and redaction semantics.
- Define canonical content hash behavior.
- Define safe trace retention rules.
- Create sample fixtures for:
  - Successful run
  - Failed model call
  - Tool call with sensitive payload
  - New CRM destination
  - Undeclared high-risk egress
  - Safe trace export
  - Signed manifest
- Build schema validation tests.
- Build conformance fixtures that every SDK must pass.

Review and bug-fix gate:

- Review schemas for compatibility with Python, TypeScript, Java, Go, and Rust.
- Review whether fields are sufficient for Agent Capsule Console.
- Review whether safe trace schema can diagnose failures without plaintext payloads.
- Fix schema gaps before SDK implementation starts.

Exit criteria:

- Schemas validate fixtures.
- Policy decisions are deterministic for fixtures.
- Conformance tests can be reused by future SDKs.

## 6. Phase 2: Python SDK Observe Mode

Goal: capture useful local traces from a real Python agent.

Tasks:

- Create the Python package.
- Implement `Capsule.init`.
- Implement run context management.
- Implement span creation and nesting.
- Capture:
  - Run ID
  - Span ID and parent span ID
  - Start and end time
  - Component name and type
  - Language runtime
  - SDK version
  - Model calls
  - Tool calls
  - Token counts
  - Payload sizes
  - Error summaries
  - Content hashes
  - Redaction markers
- Add decorators and context managers.
- Add wrappers for one model SDK.
- Add wrappers for one tool-call pattern.
- Add Pydantic-based field classification.
- Ensure Observe mode fails open with warnings when policy cannot load.
- Build a claims-triage sample app.

Review and bug-fix gate:

- Review async and nested span behavior.
- Review that raw payloads never leave local process by default.
- Review error handling and payload-size capture.
- Fix instrumentation bugs before adding CLI workflows.

Exit criteria:

- A Python sample agent produces a local trace.
- Trace fixture output passes schema validation.
- Unit tests cover success, error, and nested-call cases.

## 7. Phase 3: Local Encrypted Trace Store

Goal: persist raw traces locally while separating safe metadata from encrypted payload content.

Tasks:

- Implement local trace directory layout.
- Encrypt raw payloads at rest.
- Store metadata separately from raw payload content.
- Add retention configuration.
- Add deletion by run ID.
- Add trace listing.
- Add trace lookup by run ID.
- Add migration hooks for schema changes.
- Add tests for encryption, deletion, retention, and corrupted files.
- Ensure plaintext payloads are not logged during storage errors.

Review and bug-fix gate:

- Review encryption boundaries.
- Review failure modes for missing keys, corrupt traces, and interrupted writes.
- Review local-only behavior.
- Fix data-loss and plaintext-leak risks before continuing.

Exit criteria:

- Trace metadata can be read without decrypting payloads.
- Raw payloads are encrypted at rest.
- Deleting a run removes associated payloads.

## 8. Phase 4: CLI MVP

Goal: provide a developer entrypoint for init, observe runs, trace inspection, and policy checks.

Tasks:

- Implement `capsule init`.
- Implement `capsule run --mode observe -- <command>`.
- Implement `capsule trace list`.
- Implement `capsule manifest inspect` stub.
- Implement `capsule policy check` skeleton.
- Implement `--json` output for machine-readable commands.
- Create local config files:
  - `agent-capsule.policy.yaml`
  - `.agent-capsule/`
  - local encryption settings
- Ensure CLI output never prints raw sensitive payloads by default.
- Add command help and examples.

Review and bug-fix gate:

- Review command UX and exit codes.
- Review malformed config behavior.
- Review stdout and stderr for accidental payload exposure.
- Fix CLI safety issues before adding policy enforcement.

Exit criteria:

- Developer can initialize, run, list traces, and see safe metadata.
- CLI has unit tests and integration tests.

## 9. Phase 5: Policy Engine And Privacy Map

Goal: make privacy review part of the engineering workflow.

Tasks:

- Implement policy parser.
- Implement policy validation.
- Implement destination registry.
- Implement data-class matching.
- Implement policy actions:
  - `allow`
  - `allow_fields`
  - `redact`
  - `require_approval`
  - `block`
  - `warn`
- Implement risk classification.
- Implement undeclared destination detection.
- Implement undeclared high-risk egress detection.
- Implement policy suggestions.
- Implement privacy map generation.
- Add CRM journey fixture.
- Add `capsule policy check --fail-on high-risk-egress`.
- Add tests for field allowlists, redaction, blocking, warnings, and undeclared destinations.

Review and bug-fix gate:

- Review deterministic policy results.
- Review field-level matching behavior.
- Review false negative risk for undeclared destinations.
- Fix policy bugs before Guard mode.

Exit criteria:

- CRM journey produces an undeclared destination warning.
- CI check fails on undeclared high-risk egress.
- Suggested policy diff is usable by developers.

## 10. Phase 6: Safe Trace Export

Goal: allow useful team collaboration without exposing private payloads.

Tasks:

- Implement safe trace export.
- Remove or hash:
  - Prompt content
  - Document text
  - Model outputs
  - Tool payloads
  - Secrets
  - User identifiers
- Retain:
  - Workflow structure
  - Timing
  - Component versions
  - Error messages
  - Token counts
  - Payload sizes
  - Policy decisions
  - Content hashes
  - Redaction markers
  - SDK versions
- Add scanner tests for plaintext sensitive payloads.
- Add `capsule trace export --safe <run-id>`.
- Add safe trace import/view fixture for Agent Capsule Console.

Review and bug-fix gate:

- Review safe trace output manually and with automated scanners.
- Review whether the safe trace remains diagnostically useful.
- Fix any plaintext leakage before replay or console work continues.

Exit criteria:

- Safe trace exports contain no plaintext sensitive payloads in test fixtures.
- A teammate can inspect failure structure from a safe trace.

## 11. Phase 7: Replay

Goal: reproduce workflow behavior safely.

Tasks:

- Implement structural replay.
- Implement mocked tool replay.
- Implement mocked model response replay.
- Implement redacted payload replay.
- Implement approved local plaintext replay.
- Implement replay comparison.
- Compare:
  - Span structure
  - Timing
  - Token counts
  - Destination changes
  - Policy decision changes
  - Error changes
- Add `capsule trace replay <run-id>`.
- Add replay fixtures for success, divergence, and policy changes.

Review and bug-fix gate:

- Review replay isolation.
- Review approved plaintext reveal flow.
- Review comparison accuracy.
- Fix replay bugs before console integration.

Exit criteria:

- Failed run can be replayed structurally without plaintext export.
- Replay comparison highlights meaningful differences.

## 12. Phase 8: Agent Capsule Console

Goal: deliver the dedicated UI for encrypted traces and data-flow visibility.

Tasks:

- Create `agent-capsule-console` as a separate Next.js, TypeScript, Tailwind, and shadcn/ui codebase.
- Implement local API bridge client.
- Implement ephemeral session token handling.
- Build primary views:
  - Runs dashboard
  - Trace timeline
  - Span detail drawer
  - Data-flow graph
  - Privacy map
  - Destination review queue
  - Policy decision viewer
  - Safe trace export flow
  - Replay comparison view
  - Manifest inspector
  - Local settings page
- Implement default safe metadata rendering.
- Implement explicit local-only payload reveal confirmation.
- Add UI tests for no plaintext on first render.
- Add responsive desktop and mobile layout checks.
- Add console README with install, dev, build, and usage instructions.

Review and bug-fix gate:

- Review UI against PRD user experience requirements.
- Review that no raw payloads appear on initial render.
- Review data-flow graph accuracy.
- Review accessibility, responsive layout, and empty states.
- Fix UI and privacy bugs before Guard mode integration.

Exit criteria:

- `capsule view` opens the console through a localhost-only API bridge.
- The console displays trace timelines and data-flow visibility without plaintext payloads by default.

## 13. Phase 9: Local API Bridge

Goal: connect CLI, encrypted trace store, and Agent Capsule Console safely.

Tasks:

- Implement localhost-only server.
- Bind to `127.0.0.1` by default.
- Support ephemeral port selection.
- Support `--port`.
- Support `--no-open`.
- Support `--console-url <url>`.
- Require ephemeral session token.
- Implement endpoints:
  - `GET /health`
  - `GET /runs`
  - `GET /runs/:run_id`
  - `GET /runs/:run_id/timeline`
  - `GET /runs/:run_id/data-flow`
  - `GET /runs/:run_id/privacy-map`
  - `GET /runs/:run_id/policy-decisions`
  - `POST /runs/:run_id/export-safe-trace`
  - `POST /runs/:run_id/replay`
  - `GET /manifests/:manifest_id`
  - `POST /payloads/:payload_id/reveal-local`
- Disable payload reveal unless explicitly enabled.
- Emit audit events for reveal.
- Shut down when console session ends unless `--keep-alive` is set.

Review and bug-fix gate:

- Review auth and token handling.
- Review CORS and localhost binding.
- Review payload reveal endpoint behavior.
- Fix local API security issues before release.

Exit criteria:

- Console and CLI communicate through the local API bridge.
- Safe metadata endpoints work without decrypting raw payloads.

## 14. Phase 10: Guard Mode

Goal: enforce policies during model calls, tool calls, and supported network egress.

Tasks:

- Implement Guard mode initialization.
- Fail closed when policy cannot load.
- Evaluate policy before supported calls.
- Apply redaction before payload leaves the process.
- Block disallowed calls.
- Warn for configured warnings.
- Request human approval when required.
- Record every decision in trace metadata.
- Add tests for policy enforcement in Python sample app.
- Add error messages that explain policy violations without printing payloads.

Review and bug-fix gate:

- Review fail-closed behavior.
- Review redaction correctness.
- Review approval workflow.
- Fix bypasses before CI integration.

Exit criteria:

- Guard mode blocks undeclared high-risk egress.
- Guard mode records deterministic policy decisions.

## 15. Phase 11: Capsule Build And Signed Manifest

Goal: package an agent into a verifiable capsule artifact.

Tasks:

- Implement `capsule build`.
- Validate policy.
- Capture language runtime metadata.
- Capture package manager metadata.
- Capture dependency lockfile hashes.
- Capture container image digest when available.
- Capture prompt template hashes without prompt plaintext.
- Capture tool schemas.
- Capture model configuration.
- Capture required secrets.
- Capture network destinations.
- Sign manifest.
- Emit build report.
- Add manifest inspection.
- Add tests for missing signatures, changed dependencies, and malformed manifests.

Review and bug-fix gate:

- Review signing and hashing behavior.
- Review prompt template hashing for plaintext leakage.
- Review manifest reproducibility.
- Fix manifest bugs before confidential demo work.

Exit criteria:

- `capsule build` creates a signed manifest.
- `capsule manifest inspect` shows safe capsule evidence.

## 16. Phase 12: CI/CD Integration

Goal: make privacy policy enforcement part of pull requests.

Tasks:

- Implement `capsule ci check`.
- Implement GitHub Actions example.
- Add GitLab CI example.
- Add Buildkite example.
- Fail when:
  - Undeclared high-risk egress remains
  - Destination appears in traces but not policy
  - High-risk data class reaches unapproved destination
  - Policy file is malformed
  - Policy version is too old
  - Manifest signature is missing for release builds
  - Runtime language version is unsupported for release builds
- Add JSON output for CI annotations.
- Add docs for pull request workflows.

Review and bug-fix gate:

- Review exit codes.
- Review CI logs for payload leakage.
- Review examples for copy-paste correctness.
- Fix CI bugs before multi-language expansion.

Exit criteria:

- Pull request cannot merge if undeclared high-risk egress remains.
- CI examples are documented and tested.

## 17. Phase 13: Multi-Language SDK Beta

Goal: add TypeScript, Java, Go, and Rust SDKs with shared semantics.

Tasks:

- Implement TypeScript SDK:
  - Async context propagation
  - Model and tool wrappers
  - Zod-based field annotations
  - Conformance tests
- Implement Java SDK:
  - Builder configuration
  - Annotation-based field classification
  - HTTP and model client interceptors
  - Conformance tests
- Implement Go SDK:
  - Context propagation
  - Explicit wrappers
  - Struct tags for classification
  - Conformance tests
- Implement Rust SDK:
  - `tracing` integration
  - Serde classification
  - Tokio compatibility
  - Conformance tests
- Validate all SDKs against shared fixtures.
- Publish beta documentation.

Review and bug-fix gate:

- Review semantic parity across languages.
- Review context propagation and concurrency behavior.
- Review package ergonomics in each ecosystem.
- Fix drift before declaring beta.

Exit criteria:

- Equivalent agent runs in all supported languages produce compatible traces.
- Cross-language policy checks produce identical results for equivalent traces.

## 18. Phase 14: Confidential Demo

Goal: support private customer proof of concept flows.

Tasks:

- Implement `capsule demo create --customer <id> --mode confidential`.
- Require signed manifest.
- Require policy with no undeclared high-risk egress.
- Start supported confidential or confidential-like hosted environment.
- Verify runtime before releasing secrets.
- Integrate attestation result capture.
- Integrate secret release provider.
- Generate customer verification page.
- Restrict vendor observability to safe metadata.
- Produce sanitized support bundles.
- Add tests for failed attestation, missing secrets, policy failure, and safe vendor telemetry.

Review and bug-fix gate:

- Review attestation and secret release assumptions.
- Review customer verification page accuracy.
- Review vendor telemetry for plaintext leakage.
- Fix security and supportability bugs before enterprise deployment work.

Exit criteria:

- Startup can run a private customer POC without receiving plaintext customer data.
- Customer sees capsule identity, policy, destinations, and attestation status.

## 19. Phase 15: Product Website

Goal: implement the separate product website described in the PRD when website work is explicitly started.

Tasks:

- Create `agent-capsule-website` as a separate Next.js and TypeScript codebase.
- Initialize shadcn/ui.
- Use Tailwind CSS.
- Use US English copy.
- Build an enterprise-oriented product website.
- Enforce visual rules:
  - No emojis
  - No icons
  - No decorative icon systems
  - No icon libraries in visible UI
  - No bold fonts
  - Restrained enterprise look
- Include required sections:
  - Header
  - Hero with Agent Capsule name and clear offer
  - Product visual showing trace, policy, or data-flow evidence
  - Problem section
  - Observe, Guard, and Confidential workflow
  - Privacy review
  - Safe trace collaboration
  - Confidential demo
  - Multi-language SDK support
  - Hardware requirements
  - Enterprise evidence
  - Footer
- Add website README:
  - Install dependencies
  - Run locally
  - Build
  - Start production build
  - shadcn/ui setup
  - No emoji rule
  - No icon rule
  - No bold font rule

Review and bug-fix gate:

- Review visual design against enterprise requirements.
- Review text for overstated security claims.
- Review that no emojis or icons appear in visible UI.
- Review CSS for bold font utilities.
- Fix content, layout, accessibility, and responsive bugs before website release.

Exit criteria:

- Website runs locally.
- Website communicates private debugging, policy review, safe traces, confidential demos, supported languages, and hardware requirements.

## 20. Phase 16: Enterprise Deployment

Goal: support customer-cloud deployments and enterprise governance.

Tasks:

- Implement customer-cloud install path.
- Support customer-controlled keys.
- Implement enterprise policy approval.
- Implement egress enforcement in supported runtime.
- Implement release approvals.
- Add SSO and RBAC.
- Add SIEM integration.
- Add audit evidence export.
- Add signed billing receipts.
- Add update and rollback controls.
- Add sanitized support bundles.

Review and bug-fix gate:

- Review enterprise threat model.
- Review customer access boundaries.
- Review evidence export correctness.
- Review update and rollback behavior.
- Fix governance and deployment bugs before GA.

Exit criteria:

- Enterprise can approve, install, verify, monitor, update, and roll back an Agent Capsule in its own environment.

## 21. Cross-Phase Testing Strategy

Required test layers:

- Unit tests for SDK, CLI, policy engine, trace store, local API, and UI components.
- Integration tests for first developer experience.
- End-to-end tests for:
  - Observe mode trace capture
  - Privacy review
  - Safe trace export
  - Replay
  - Guard mode blocking
  - CI policy failure
  - Capsule build
  - Console inspection
  - Confidential demo
- Schema conformance tests for every SDK.
- Security tests for plaintext leakage.
- Snapshot fixtures for safe traces and manifests.
- Browser tests for Agent Capsule Console and product website.
- Build tests for every package and codebase.

Minimum checks before phase completion:

```bash
capsule policy check
capsule ci check
```

Also run the relevant package checks for changed codebases:

- Python: format, lint, type check, unit tests, integration tests.
- TypeScript and Next.js: lint, type check, unit tests, build, browser tests.
- Java: format, unit tests, package build.
- Go: format, vet, unit tests.
- Rust: format, clippy, unit tests.

## 22. Code Review And Bug-Fix Protocol

Every phase must end with a code review.

Review priorities:

- Data privacy leaks
- Incorrect policy decisions
- Broken encryption or key handling
- Unsafe plaintext logging
- CI false negatives
- Cross-language semantic drift
- UI revealing raw payloads by default
- Missing tests for high-risk behavior
- Broken developer setup
- Accessibility and responsive layout issues

Review process:

1. Inspect changed files.
2. Run tests and builds.
3. Record findings by severity.
4. Fix every blocking and high-severity issue.
5. Add regression tests for each fixed bug.
6. Re-run relevant checks.
7. Update docs if behavior changed.

Bug-fix rule:

- Do not start the next implementation phase while known high-severity bugs remain.
- Do not defer privacy, encryption, policy, or plaintext-leak bugs.
- If a bug cannot be fixed immediately, document the blocker, mitigation, owner, and release impact.

## 23. Security And Privacy Review Checklist

Before release, verify:

- Raw payloads remain local by default.
- Local raw traces are encrypted at rest.
- Safe trace exports contain no plaintext sensitive payloads.
- CI logs do not print raw payloads.
- Policy decisions are recorded without blocked plaintext payloads.
- Payload reveal requires explicit local confirmation.
- Reveal actions are audited locally.
- Undeclared high-risk egress blocks release builds.
- Secrets are blocked unless destination is explicitly approved as a secrets provider.
- Confidential mode releases secrets only after verification.
- Product website does not overstate guarantees.

## 24. Documentation Deliverables

Required docs:

- SDK quickstart
- CLI command reference
- Policy authoring guide
- Safe trace guide
- Replay guide
- Agent Capsule Console guide
- Local API bridge guide
- CI/CD guide
- Capsule manifest guide
- Confidential demo guide
- Hardware and runtime requirements
- Product website README
- Troubleshooting guide
- Security model
- Known limitations and non-goals

## 25. Final Release Checklist

Before declaring the product ready:

- All MVP acceptance criteria in `PRD.md` are satisfied.
- All phase exit criteria are satisfied.
- All high-severity review findings are fixed.
- All conformance fixtures pass.
- All safe trace scanner tests pass.
- All docs are current.
- Agent Capsule Console works from `capsule view`.
- CI fails undeclared high-risk egress.
- Signed manifest generation works.
- Claims-triage sample demonstrates first developer experience, privacy review, safe trace, replay, and capsule build.


# Phase 13 Review: Multi-Language SDK Beta

## Scope Reviewed

- TypeScript SDK beta with async context propagation, wrappers, Zod annotations, and conformance tests.
- Java SDK beta with builder configuration, annotations, HTTP/model interceptors, explicit async propagation, and a plain Java conformance test.
- Go SDK beta with context propagation, explicit wrappers, struct tags, and shared fixture tests.
- Rust SDK beta with tracing integration, serde classification, Tokio-compatible async wrappers, and shared fixture tests.
- Cross-language safe trace fixtures and validator.

## Semantic Parity

All SDKs implement the shared policy-decision semantics for:

- Declared destination allow.
- Declared destination redaction.
- Declared destination human approval.
- Allow-fields filtering decisions.
- Undeclared high-risk egress block.
- Undeclared medium-risk destination warning.
- Secret blocking before destination rules.

`ci/validate-phase13.py` compares the shared policy decision fixture and verifies equivalent safe trace signatures for TypeScript, Java, Go, and Rust.

## Context Propagation

- TypeScript uses `AsyncLocalStorage`.
- Java uses a `ThreadLocal` run context plus an explicit `propagate` helper for executor and `CompletableFuture` boundaries.
- Go carries run state through `context.Context`.
- Rust keeps run state in the `Capsule` handle and records spans inside async wrapper calls, with `tracing` spans around each wrapped call.

## Package Ergonomics

- TypeScript uses npm scripts for typecheck and tests.
- Java intentionally avoids Gradle or Maven in the beta so conformance can run with only `javac`.
- Go uses standard `go test`.
- Rust uses Cargo, serde, tracing, sha2, and Tokio tests.

## Toolchain Review

This local environment has Node.js available, so TypeScript native tests were run. Java, Go, and Rust source/tests are included and are run conditionally by `ci/check-phase13.sh` when their toolchains are installed. The cross-language validator always runs and enforces safe trace and policy parity.

## Payload Leakage Review

The SDKs and fixtures emit safe metadata only: hashes, sizes, data classes, destinations, policy decisions, and redaction markers. The Phase 13 validator scans fixture traces for known raw payload strings.

## Verification

Run:

```bash
bash ci/check-phase13.sh
```

This runs previous phase checks, TypeScript native tests, available Java/Go/Rust native tests, and cross-language fixture validation.

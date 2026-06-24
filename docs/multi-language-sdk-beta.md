# Multi-Language SDK Beta

Phase 13 adds beta SDKs for TypeScript, Java, Go, and Rust. The beta goal is semantic parity with the Python SDK and policy engine, not final packaging polish.

## Shared Semantics

Every SDK beta implements the same core behavior:

- Policy evaluation for `allow`, `allow_fields`, `redact`, `require_approval`, `block`, `warn`, and `not_evaluated`.
- Data class risk classification for the shared data-class vocabulary.
- Destination-aware model and tool wrappers or interceptors.
- Safe trace metadata with hashes, payload sizes, data classes, destinations, policy decisions, and redaction markers.
- Conformance against `fixtures/conformance/policy-decisions.json`.

Cross-language trace fixtures live in `fixtures/conformance/traces/` and are validated by `ci/validate-phase13.py`.

## TypeScript

Location: `sdk-typescript/`

Implemented beta surface:

- `AsyncLocalStorage` run context propagation.
- `wrapTool` and `wrapModel` wrappers.
- Zod transform helper for classified fields.
- Native Node test runner conformance tests.

Run:

```bash
cd sdk-typescript
npm ci
npm run typecheck
npm test
```

## Java

Location: `sdk-java/`

Implemented beta surface:

- Builder configuration.
- `@DataClass` annotation-based field classification.
- HTTP and model interceptors.
- Explicit async context propagation helper for executor boundaries.
- Plain `javac` conformance test entrypoint.

Run when a JDK is installed:

```bash
cd sdk-java
mkdir -p build/classes
find src/main/java src/test/java -name '*.java' | sort > build/sources.txt
javac -d build/classes @build/sources.txt
java -cp build/classes dev.agentcapsule.ConformanceTest
```

## Go

Location: `sdk-go/`

Implemented beta surface:

- `context.Context` run propagation.
- Explicit `WrapTool` and `WrapModel` functions.
- Struct tag classification with `capsule:"data_class"`.
- Shared fixture tests through Go's standard JSON tooling.

Run when Go is installed:

```bash
cd sdk-go
go test ./...
```

## Rust

Location: `sdk-rust/`

Implemented beta surface:

- `tracing` span integration around wrapped calls.
- Serde JSON classification.
- Async wrappers with Tokio compatibility tests.
- Shared fixture tests through `serde_json`.

Run when Cargo is installed:

```bash
cd sdk-rust
cargo test
```

## Phase Check

Run all available native checks plus cross-language fixture validation:

```bash
bash ci/check-phase13.sh
```

The script runs TypeScript tests in this repository, runs Java/Go/Rust native tests when their toolchains are installed, and always validates cross-language safe trace fixtures.

## Beta Limits

- Java, Go, and Rust package publishing metadata is intentionally minimal.
- Java redaction transforms are conservative in the beta; policy decisions and trace evidence are implemented, while rich object rewriting is reserved for package-hardening work.
- Rust classification uses serde JSON values in the beta instead of a derive macro.
- Cross-language traces are safe metadata fixtures; they do not contain raw prompts, documents, model outputs, tool payloads, secrets, or user identifiers.

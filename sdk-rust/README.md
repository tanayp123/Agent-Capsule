# Rust SDK

Purpose: Rust instrumentation for safety-sensitive, high-performance, and edge agent runtimes.

Phase 13 status: beta implementation.

Tooling:

- Rust stable
- Cargo
- rustfmt
- clippy
- cargo test

Implemented beta features:

- `tracing` integration
- Serde-based field classification
- Tokio compatibility
- Shared schema conformance tests

## Run Tests

```bash
cargo test
```

The Rust SDK uses serde JSON classification in the beta, records tracing spans around wrapped calls, and includes Tokio tests for async wrapper behavior.

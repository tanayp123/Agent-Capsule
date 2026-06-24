# Conformance Fixtures

These fixtures define deterministic behavior every SDK must pass.

`policy-decisions.json` contains policy evaluation cases that must produce the same result in Python, TypeScript, Java, Go, and Rust.

`traces/` contains equivalent safe trace metadata fixtures for the Phase 13 TypeScript, Java, Go, and Rust SDK beta. These traces are compared by `ci/validate-phase13.py` and must not contain plaintext payloads.

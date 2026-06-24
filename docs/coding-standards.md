# Coding Standards

## General

- Keep changes scoped to the active phase.
- Prefer simple, explicit code over broad abstractions.
- Add comments only when they clarify non-obvious behavior.
- Never log raw prompts, documents, model outputs, tool payloads, secrets, or user identifiers.
- Keep behavior deterministic where policy, hashing, redaction, and schema validation are involved.
- Add regression tests for each bug fix.

## Python

- Use Python 3.10+.
- Use type hints for public APIs.
- Use dataclasses or Pydantic models for structured trace and policy data.
- Use Ruff for format and lint.
- Use mypy for type checking once implementation starts.
- Use pytest for tests.

## TypeScript

- Use strict TypeScript.
- Keep generated shadcn/ui components in `components/ui`.
- Keep product-specific components outside `components/ui`.
- Avoid bold font utilities in the product website.
- Do not use emojis or icons in the product website visible UI.
- Use Playwright to verify key console and website views.

## Java

- Target Java 17+.
- Prefer builder-style public configuration.
- Use annotation-based classification where it fits JVM conventions.
- Keep policy semantics aligned with shared fixtures.

## Go

- Use context propagation for trace and policy context.
- Use explicit wrappers rather than hidden global state.
- Use struct tags for field classification where appropriate.
- Keep generated trace data schema-compatible.

## Rust

- Integrate with `tracing`.
- Use Serde for structured data.
- Prefer explicit error types.
- Keep async runtime assumptions clear.

## Documentation

- Every codebase must include a README before implementation begins.
- README files must document setup, run, test, and build commands as soon as they exist.
- Security-sensitive behavior must be documented near the code that implements it.


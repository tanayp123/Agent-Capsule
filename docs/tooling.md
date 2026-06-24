# Tooling Choices

These choices establish defaults for Phase 0. Later phases may refine them if implementation evidence shows a better fit.

## Python SDK And CLI

- Runtime: Python 3.10+
- Package manager: `uv` preferred, `pip` supported
- Build metadata: `pyproject.toml`
- Build backend: Hatchling preferred
- Runtime dependencies:
  - `cryptography` for authenticated local payload encryption
  - local `policy-engine` package for deterministic policy evaluation
- Formatting and linting: Ruff
- Type checking: mypy
- Tests: pytest

The Python SDK is the MVP wedge. The CLI may start as a Python package so it can share early trace-store and policy-engine code.

## TypeScript SDK, Console, And Website

- Runtime: Node.js 20+
- Package manager: pnpm preferred, npm supported
- Framework for console: Next.js with App Router
- Framework for website: Next.js with App Router
- UI system: shadcn/ui
- Styling: Tailwind CSS
- Tests: Vitest for units, Playwright for browser flows
- Type checking: TypeScript
- Linting: ESLint

The console and website must remain separate codebases.

The Agent Capsule Console begins in Phase 8 as a Next.js App Router application in `agent-capsule-console/`, with shadcn/ui-style primitives, Tailwind CSS, and Playwright checks for privacy and responsive rendering. Phase 9 connects it to the encrypted trace store through the localhost-only local API bridge started by `capsule view`.

## Java SDK

- Runtime: Java 17+
- Build tool: Gradle preferred
- Tests: JUnit
- Formatting and static checks: Gradle-managed tools selected during SDK implementation

## Go SDK

- Runtime: Go 1.22+
- Build tool: standard Go toolchain
- Formatting: gofmt
- Static checks: go vet
- Tests: go test

## Rust SDK

- Runtime: Rust stable
- Build tool: Cargo
- Formatting: rustfmt
- Static checks: clippy
- Tests: cargo test

## Shared Artifacts

- Schemas: JSON Schema
- Policy examples: YAML
- Fixtures: JSON and YAML
- CI: GitHub Actions first, with GitLab CI and Buildkite examples in later phases

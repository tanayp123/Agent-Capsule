# CI

This directory contains repository-level CI scripts and examples.

Phase 0 provides a foundation check that validates the expected repository structure and documentation exist before implementation starts.

Run locally:

```bash
bash ci/check-foundation.sh
```

Run Phase 1 schema and conformance checks:

```bash
bash ci/check-phase1.sh
```

Run Phase 2 Python observe-mode checks:

```bash
bash ci/check-phase2.sh
```

Run Phase 3 encrypted trace-store checks:

```bash
bash ci/check-phase3.sh
```

Run Phase 4 CLI MVP checks:

```bash
bash ci/check-phase4.sh
```

Run Phase 5 policy engine and privacy-map checks:

```bash
bash ci/check-phase5.sh
```

Run Phase 6 safe trace export checks:

```bash
bash ci/check-phase6.sh
```

Run Phase 7 replay checks:

```bash
bash ci/check-phase7.sh
```

Run Phase 8 console checks:

```bash
bash ci/check-phase8.sh
```

Run Phase 9 local API bridge checks:

```bash
bash ci/check-phase9.sh
```

Run Phase 10 Guard Mode checks:

```bash
bash ci/check-phase10.sh
```

Run Phase 11 capsule build checks:

```bash
bash ci/check-phase11.sh
```

Run Phase 12 CI/CD integration checks:

```bash
bash ci/check-phase12.sh
```

Run Phase 13 multi-language SDK beta checks:

```bash
bash ci/check-phase13.sh
```

Run Phase 14 confidential demo checks:

```bash
bash ci/check-phase14.sh
```

Run Phase 15 product website checks:

```bash
bash ci/check-phase15.sh
```

Copy-paste CI examples are available in `ci/examples/`:

- `github-actions-agent-capsule.yml`
- `gitlab-ci-agent-capsule.yml`
- `buildkite-agent-capsule.yml`

Future phases will add package-specific jobs for:

- Python formatting, linting, type checking, and tests.
- TypeScript linting, type checking, tests, and Next.js builds.
- Java formatting, tests, and package build.
- Go formatting, vetting, and tests.
- Rust formatting, clippy, and tests.
- Expanded schema validation and cross-language conformance fixtures.

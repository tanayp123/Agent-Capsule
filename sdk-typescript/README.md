# TypeScript SDK

Purpose: TypeScript and JavaScript instrumentation for Node.js agent services.

Phase 13 status: beta implementation.

Tooling:

- Node.js 20+
- npm
- TypeScript
- Node test runner
- Zod

Implemented beta features:

- Async context propagation
- Model and tool wrappers
- Zod-based field annotations
- Shared schema conformance tests

## Run Tests

```bash
npm ci
npm run typecheck
npm test
```

The SDK mirrors the shared policy-decision fixture in `fixtures/conformance/policy-decisions.json` and emits safe trace metadata without raw payload values.

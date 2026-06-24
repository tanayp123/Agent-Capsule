# Go SDK

Purpose: Go instrumentation for backend and infrastructure-heavy agent services.

Phase 13 status: beta implementation.

Tooling:

- Go 1.22+
- gofmt
- go vet
- go test

Implemented beta features:

- Context propagation
- Explicit wrapper functions
- Struct tags for field classification
- Shared schema conformance tests

## Run Tests

```bash
go test ./...
```

The Go SDK carries active run state through `context.Context`, exposes explicit model/tool wrappers, and reads shared JSON fixtures with the standard library.

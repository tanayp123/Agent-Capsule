# Phase 6 Review

## Scope Reviewed

- Safe trace export from encrypted trace-store metadata.
- CLI command `capsule trace export --safe <run-id>`.
- Plaintext scanner behavior for sensitive keys, email-like values, API-key-like values, and known raw fixture payloads.
- Console import fixture compatibility with `safe-trace.schema.json`.

## Findings Fixed

- Replaced email-like `created_by` fixture data with `local-developer`.
- Added error-message sanitization before safe trace serialization.
- Added scanner tests for reserved sensitive keys and sensitive-looking plaintext.
- Ensured the exporter reads payload-index hashes but does not decrypt payload sidecars.

## Residual Risks

- Error messages are retained after pattern-based sanitization; future phases should add configurable organization-specific scanners.
- The safe trace schema is metadata-oriented and does not yet carry richer replay hints.

## Verification

```bash
bash ci/check-phase6.sh
```

# Phase 7 Review

## Scope Reviewed

- Structural replay from trace metadata.
- Mocked model and tool replay from hash-only payload references.
- Redacted payload replay.
- Approved local plaintext verification.
- Replay comparison for structure, timing, token counts, destinations, policy decisions, and errors.
- CLI command `capsule trace replay <run-id>`.

## Findings Fixed

- Added an explicit `--approve-plaintext` gate for approved plaintext replay.
- Kept approved plaintext verification local and omitted raw payload values from serialized replay artifacts.
- Added raw-value scanner checks across generated replay artifacts and CLI outputs.
- Added fixtures for success, divergence, and policy-change comparison.

## Residual Risks

- Replay is structural and mocked in Phase 7; it does not execute user agent code.
- Approved plaintext replay verifies stored payloads but does not yet provide an interactive reveal flow.
- Replay fixture schemas are not formalized yet; later console work may add a JSON schema.

## Verification

```bash
bash ci/check-phase7.sh
```

# Phase 9 Review

## Scope Reviewed

- Localhost-only API bridge server.
- `capsule view` local bridge startup and session-token URL generation.
- Console client integration with local bridge endpoints.
- Payload reveal endpoint, CORS behavior, and session shutdown.
- Phase 9 CI checks.

## Review Findings And Fixes

- The initial reveal route accepted `POST /payloads/:payload_id`; it now requires the exact `POST /payloads/:payload_id/reveal-local` path.
- Manifest reads now fail closed with `404` when no manifest is configured instead of returning a successful response with an error object.
- Payload reveal attempts are audited before lookup, so disabled reveal mode does not disclose whether a payload exists.
- `capsule view` now starts a localhost bridge on `127.0.0.1` with an ephemeral session token and selected port, rather than only formatting a console URL.
- The console client now handles local API response shapes, uses `POST /runs/:run_id/replay`, and signals `POST /session/end` on page unload.

## Security Checklist

- Auth: every non-preflight endpoint requires `Authorization: Bearer <token>` or `X-Agent-Capsule-Session`.
- Binding: server creation rejects non-local hosts and defaults to `127.0.0.1`.
- CORS: browser access is limited to localhost origins, with optional exact console-origin matching.
- Safe metadata: run, timeline, data-flow, privacy-map, policy-decision, safe-trace export, replay, and manifest endpoints avoid plaintext payload values.
- Reveal: raw payload reveal is disabled by default, requires process startup with `--enable-payload-reveal`, and writes audit events.

## Residual Risk

- Session shutdown depends on browser page lifecycle delivery. `--keep-alive` is explicit for workflows that need a persistent bridge.
- The bridge is intentionally local developer tooling and does not replace a production API gateway or remote auth layer.

## Verification

- `python3 -m unittest local-api/tests/test_local_api.py cli/tests/test_cli.py`
- `npm run build` in `agent-capsule-console`
- `npm run test:ui` in `agent-capsule-console`
- `bash ci/check-phase9.sh`

# Phase 10 Review

## Scope Reviewed

- Python SDK Guard Mode initialization and policy loading.
- Pre-egress policy evaluation for supported model and tool wrappers.
- Redaction and allow-fields transformations.
- Block, warn, and human approval behavior.
- Claims-triage sample enforcement under restrictive policy.
- Phase 10 CI checks.

## Review Findings And Fixes

- Policy decisions previously happened when a span was appended, after wrapped calls had already run. The SDK now evaluates policy before supported wrapper calls.
- Guard Mode now fails closed when a policy is missing or malformed by raising `PolicyViolationError`.
- `block` decisions prevent the wrapped function from running and record a `blocked` span.
- `redact` and `allow_fields` now transform outbound call arguments before egress while trace metadata still records deterministic decisions and hashes.
- `require_approval` now fails closed without an approval handler and passes only safe metadata to an approval handler when configured.

## Security Checklist

- Fail closed: Guard and Confidential modes reject missing or invalid policy.
- Redaction: configured field/data-class values are replaced before supported calls.
- Allow fields: known classified fields outside the selected allowlist are removed or replaced before supported calls.
- Approval: approval requests contain IDs, fields, content hashes, and sizes, not plaintext payloads.
- Blocking: disallowed supported calls are not invoked.
- Errors: policy violation messages include component, destination, reason, and field names without payload values.

## Residual Risk

- Phase 10 enforces supported Python SDK wrappers. Direct unwrapped network clients remain outside SDK control until later language/runtime integrations.
- Generic redaction preserves common dictionaries, dataclasses, lists, tuples, sets, and classified fields; unusual custom objects should be wrapped or converted before egress.

## Verification

- `python3 -m unittest discover -s sdk-python/tests`
- `bash ci/check-phase10.sh`

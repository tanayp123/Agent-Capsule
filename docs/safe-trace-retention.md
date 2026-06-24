# Safe Trace Retention

Safe traces are designed for team debugging without exposing plaintext sensitive payloads.

## Safe Trace Export

Safe trace export must remove or hash:

- Prompt content
- Document text
- Model outputs
- Tool payloads
- Secrets
- User identifiers
- Customer identifiers unless explicitly classified as shareable

Safe trace export must retain:

- Workflow structure
- Timing
- Component versions
- Error messages
- Token counts
- Payload sizes
- Policy decisions
- Content hashes
- Redaction markers
- Language runtime metadata
- SDK versions

## Retention Rules

Default local retention:

- Raw encrypted traces: configurable, default 14 days.
- Safe traces: configurable, default 30 days.
- CI artifacts: safe traces only, default controlled by CI provider.

Retention must be deletable by run ID or trace ID.

Phase 3 implements deletion by run ID and retention deletion for raw encrypted traces. Phase 6 implements safe trace export and plaintext scanning. Safe trace retention policy remains configurable in later packaging and UI work.

## Sharing Rules

Safe traces may be shared with teammates if they pass plaintext scanning.

Safe traces must not contain:

- `raw_payload`
- `prompt`
- `document_text`
- `model_output`
- `tool_payload`
- `secret`
- `api_key`
- `access_token`

These names are reserved for scanner checks and should not appear as safe trace payload fields.

## CLI Export

Export a safe trace from local metadata:

```bash
python3 -m agent_capsule_cli trace export --safe run_123 --output safe-trace.json
```

The exporter reads trace metadata and payload-index hashes. It does not decrypt encrypted payload sidecars.

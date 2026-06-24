# Security Baseline

Security and privacy behavior must be designed into every phase.

## Default Privacy Rules

- Raw prompts remain local by default.
- Raw documents remain local by default.
- Raw model outputs remain local by default.
- Raw tool payloads remain local by default.
- Secrets remain local by default.
- User identifiers remain local by default.
- Remote sync is disabled by default.
- CI output must not include raw trace payloads.

## Logging Rules

Do not log:

- API keys
- Access tokens
- Prompt content
- Document text
- Model outputs
- Tool payloads
- Secrets
- User identifiers
- Customer identifiers unless explicitly classified as shareable metadata

Log only safe metadata by default:

- Run ID
- Span ID
- Component type
- Timing
- Payload size
- Token count
- Error class or summary
- Policy decision
- Destination ID
- Content hash
- Redaction marker

## Local Storage Rules

- Raw payloads are encrypted at rest in payload sidecar files.
- Metadata and raw payload content are stored separately.
- Deleting a run must remove associated metadata, payload indexes, and encrypted payloads.
- Corrupted payload files must fail safely without printing plaintext.
- Phase 3 uses local Fernet keys stored under the trace-store root by default. Future phases may move key storage to OS keychains, customer-managed keys, or enterprise key-management services.

## CI Rules

- CI must run without access to raw local trace payloads.
- CI must fail on undeclared high-risk egress once policy checks are implemented.
- CI annotations must use safe metadata only.

## Product Website Rules

- Do not overstate security guarantees.
- Do not claim Agent Capsule eliminates prompt injection.
- Do not claim Agent Capsule guarantees complete AI safety.
- Do not imply a GPU is required for Agent Capsule itself.
- Distinguish local development requirements from confidential cloud requirements.

# Hashing And Redaction Semantics

Hashing and redaction must be deterministic across SDKs.

## Canonical Content Hash

The canonical content hash format is:

```text
sha256:<lowercase-hex-digest>
```

Rules:

- Hash UTF-8 encoded bytes.
- Normalize structured JSON payloads before hashing.
- JSON normalization uses sorted object keys, no insignificant whitespace, and stable primitive encoding.
- Do not include local file paths, memory addresses, timestamps, or process IDs in content hashes.
- Do not hash secrets directly if the hash would enable offline guessing of a low-entropy secret; record a redaction marker instead.

## Redaction Markers

Redaction markers must be explicit and machine-readable.

Recommended marker format:

```text
redacted:<data-class>
```

Examples:

- `redacted:email`
- `redacted:document_text`
- `redacted:secrets`
- `hashed:prompt_content`

## Field Redaction

Field redaction replaces the original value with a marker and records the data class.

Example:

```json
{
  "email": "redacted:email"
}
```

## Safe Trace Hashes

Safe traces may include content hashes for comparison and replay diagnostics, but must not include raw payloads.

Safe traces must not include:

- Prompt text
- Document text
- Model output text
- Tool payload values
- Secrets
- User identifiers

## Language Compatibility

Every SDK must produce the same hash for equivalent normalized payloads. Cross-language conformance tests must verify this before SDK beta.


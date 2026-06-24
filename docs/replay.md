# Replay

Replay reproduces trace structure safely for debugging without exporting plaintext payloads by default.

## Modes

- `structural`: rebuilds workflow structure from trace metadata.
- `mocked`: creates mocked model and tool results from content hashes, token counts, and payload indexes.
- `redacted`: includes redacted payload references such as `[redacted:input]`.
- `approved_plaintext`: decrypts payloads locally only after explicit approval, verifies content hashes, and discards plaintext before serializing the replay artifact.

## Comparison

Replay comparison checks:

- Span structure
- Timing
- Token counts
- Destination changes
- Policy decision changes
- Error changes

Comparison output is metadata only and is suitable for local diagnosis or future console rendering.

## CLI

```bash
python3 -m agent_capsule_cli trace replay run_123 --mode structural --output replay.json
python3 -m agent_capsule_cli trace replay run_123 --mode mocked --output mocked-replay.json
python3 -m agent_capsule_cli trace replay run_123 --compare mocked-replay.json --json
```

Approved plaintext mode requires explicit consent:

```bash
python3 -m agent_capsule_cli trace replay run_123 --mode approved_plaintext --approve-plaintext
```

Approved plaintext mode never writes plaintext payload values into the replay artifact.

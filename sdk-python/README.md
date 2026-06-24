# Python SDK

Purpose: first SDK wedge for instrumenting Python agents.

Phase 10 status: Observe mode, Guard Mode, local encrypted trace store, policy decisions, safe trace export, and replay implemented.

Planned tooling:

- Python 3.10+
- `uv` preferred, `pip` supported
- `pyproject.toml`
- Hatchling build backend
- Ruff
- mypy
- pytest

Planned features:

- `Capsule.init`
- Run context manager
- Span recording
- Model-call wrappers
- Tool-call wrappers
- Pydantic-based field classification
- Observe mode first

## Run Tests

From the repository root:

```bash
PYTHONPATH=sdk-python/src python3 -m unittest discover -s sdk-python/tests
```

## Minimal Usage

```python
from agent_capsule import Capsule, Destination

capsule = Capsule.init(mode="observe", trace_dir=".agent-capsule/traces")

model_destination = Destination(
    id="model_provider",
    type="model_provider",
    domain="api.model.example",
    provider="Example Model",
)

def classify_claim(claim):
    return "approved"

classify_claim = capsule.wrap_model_client(
    classify_claim,
    component_name="classify-claim",
    destination=model_destination,
)

with capsule.run("claim-triage") as run:
    result = classify_claim({"policy_number": "POL-123"})
    run.record_output(result)
```

The SDK writes safe trace metadata to `metadata/` and encrypted raw payload sidecars to `payloads/`. Metadata records payload sizes, content hashes, data classes, and redaction markers. Raw payload bodies are encrypted at rest and kept separate from metadata.

Export a safe trace from local metadata:

```python
from agent_capsule import export_safe_trace_from_store

safe_trace = export_safe_trace_from_store(capsule.trace_store, run.run_id)
```

Safe trace export retains workflow structure, timing, component versions, errors, token counts, payload sizes, policy decisions, content hashes, and redaction markers without decrypting raw payload sidecars.

Replay a trace from local metadata:

```python
from agent_capsule import replay_trace_from_store

replay = replay_trace_from_store(capsule.trace_store, run.run_id, mode="structural")
```

Compare a replay artifact:

```python
from agent_capsule import compare_trace_to_replay

trace = capsule.trace_store.find_trace_by_run_id(run.run_id)
comparison = compare_trace_to_replay(trace, replay)
```

Approved local plaintext replay requires `approve_plaintext=True`. The replay artifact records verification metadata and does not include plaintext payload values.

## Guard Mode

Guard Mode enforces policy before supported model and tool wrapper calls:

```python
from agent_capsule import Capsule, Destination

def approve(request):
    # Request contains IDs, policy fields, hashes, and sizes, not plaintext payloads.
    return request["decision_action"] == "require_approval"

capsule = Capsule.init(
    mode="guard",
    policy="agent-capsule.policy.json",
    trace_dir=".agent-capsule/traces",
    approval_handler=approve,
)
```

Guard Mode fails closed if the policy cannot load. `block` prevents the wrapped call from running, `redact` replaces configured fields before the call, `allow_fields` removes disallowed classified fields, `warn` records a warning while proceeding, and `require_approval` calls the approval handler before proceeding.

## Phase Checks

From the repository root:

```bash
bash ci/check-phase2.sh
bash ci/check-phase3.sh
bash ci/check-phase6.sh
bash ci/check-phase7.sh
bash ci/check-phase10.sh
```

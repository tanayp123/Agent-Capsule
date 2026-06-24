# Claims Triage Python Example

Purpose: demonstrate the primary Agent Capsule workflow using a Python claims-triage agent.

Phase 11 status: sample supports Observe mode, Guard Mode, and signed manifest build evidence.

Planned workflow:

1. Install Python SDK.
2. Run the sample agent in Observe mode.
3. Capture a local encrypted trace.
4. Detect an undeclared destination.
5. Generate policy suggestions.
6. Export a safe trace.
7. Replay a failed run.
8. Build a signed capsule manifest.

Implemented in Phase 2:

- Observe-mode trace capture
- Model-call wrapper
- Tool-call wrapper
- Dataclass field classification
- Local trace metadata output

Run from the repository root:

```bash
PYTHONPATH=sdk-python/src python3 examples/claims-triage-python/claims_triage.py --trace-dir /tmp/agent-capsule-claims-trace
```

Run the sample with Guard Mode and a restrictive policy:

```bash
source ci/python-env.sh
AGENT_CAPSULE_MODE=guard \
AGENT_CAPSULE_POLICY=fixtures/policies/restrictive-policy.json \
python3 examples/claims-triage-python/claims_triage.py --trace-dir /tmp/agent-capsule-guard-trace
```

The restrictive Guard Mode command is expected to fail closed before the first blocked egress call, while still writing safe trace metadata. In Observe mode, the command prints the generated trace path. The trace contains metadata, hashes, payload sizes, data classes, destinations, policy warnings, and redaction markers. It does not persist raw payload bodies.

Build a signed capsule manifest for the sample:

```bash
source ci/python-env.sh
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli build \
  --policy fixtures/policies/crm-policy.json \
  --output .agent-capsule/manifests/claims-triage-manifest.json \
  --prompt-template claim_classification=examples/claims-triage-python/claim-classification.prompt \
  --tool-schema crm.upsert_account:1.0.0:examples/claims-triage-python/crm-tool.schema.json \
  --model-provider "Example Model" \
  --model example-large \
  --required-secret MODEL_PROVIDER_API_KEY \
  --required-secret CRM_API_KEY \
  --usage-meter claim_count:claim \
  --usage-meter model_tokens:token
```

The manifest stores hashes for prompts and schemas, not prompt plaintext.

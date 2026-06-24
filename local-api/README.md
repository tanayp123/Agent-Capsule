# Local API Bridge

Purpose: localhost-only API bridge between the CLI, encrypted trace store, and Agent Capsule Console.

Phase 9 status: implemented.

## Behavior

- Bind to `127.0.0.1` by default
- Use an ephemeral port unless `--port` is configured
- Require an ephemeral session token on every API request
- Return safe metadata by default
- Gate plaintext reveal behind explicit `--enable-payload-reveal`
- Audit local reveal attempts and reveals
- Shut down when the console calls `POST /session/end`, unless `--keep-alive` is set

## Run Directly

```bash
source ci/python-env.sh
TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
python3 -m agent_capsule_local_api \
  --trace-dir .agent-capsule/traces \
  --policy agent-capsule.policy.yaml \
  --port 0 \
  --session-token "$TOKEN"
```

The startup line prints the selected localhost port and session token as JSON.

## Endpoints

- `GET /health`
- `GET /runs`
- `GET /runs/:run_id`
- `GET /runs/:run_id/timeline`
- `GET /runs/:run_id/data-flow`
- `GET /runs/:run_id/privacy-map`
- `GET /runs/:run_id/policy-decisions`
- `POST /runs/:run_id/export-safe-trace`
- `POST /runs/:run_id/replay`
- `POST /runs/:run_id/evidence-package`
- `GET /evidence-packages/:package_id/verify`
- `GET /evidence-packages/:package_id/customer-report`
- `POST /live-agents/:agent_id/run`
- `POST /live-agents/:agent_id/scenario-suite`
- `GET /manifests/:manifest_id`
- `POST /payloads/:payload_id/reveal-local`
- `POST /session/end`

## Live Agent Test

`POST /live-agents/:agent_id/run` runs a representative local agent workflow through the Python SDK instrumentation. The request can include `scenario_id` with one of `sensitive-crm-egress`, `metadata-only-check`, or `approval-required`. The endpoint writes encrypted payload sidecars to the local trace store, exports a safe trace, generates a privacy map, audits the test capture, and returns only safe metadata to the browser.

The endpoint supports the demo console's ten agent IDs. Unknown IDs use a generic external-tool profile so every selected agent can still produce a trace-shaped privacy review.

The response includes:

- `run`: safe run metadata
- `test_scenario`: selected scenario name, expected result, data classes, and destination ID
- `test_result`: safe result status, finding summary, encrypted payload count, and safe-payload attestation
- `safe_trace`: redacted timeline, workflow graph, component versions, payload sizes, token counts, policy decisions, content hashes, and redaction markers
- `privacy_map`: destinations, data classes, findings, and policy suggestions
- `proof`: safe-trace readiness, encrypted payload count, redaction markers, and policy finding count

`POST /live-agents/:agent_id/scenario-suite` runs every built-in scenario for the selected agent. It creates encrypted traces for each scenario and returns a safe suite summary with scenario IDs, run IDs, trace IDs, finding counts, encrypted payload counts, and safe-payload attestation. It does not return plaintext prompts, documents, model outputs, tool bodies, secrets, or user identifiers. The console can then open any suite result by using the returned `run_id` with `GET /runs/:run_id/timeline` and `GET /runs/:run_id/privacy-map`.

## Evidence Package

`POST /runs/:run_id/evidence-package` builds a share-safe review artifact for a selected run. The request may include a selected policy response:

```json
{
  "policy_response": {
    "action": "redact",
    "title": "Redact fields",
    "outcome": "Email and account notes are redacted before CRM egress.",
    "ci_status": "CI gate: passes when redaction markers are present.",
    "patch_preview": ["crm_tool:", "  redact: [email, account_notes]"]
  }
}
```

The response includes safe run metadata, safe trace, privacy map, selected policy response, manifest summary, CI gate summary, and redaction attestation. It does not include plaintext prompts, documents, model outputs, tool payloads, secrets, or user identifiers.

The bridge also writes the package to:

```text
.agent-capsule/evidence/<package_id>.json
.agent-capsule/evidence/<package_id>.json.sha256
```

The `.sha256` sidecar is a detached SHA-256 hash of the saved JSON package. The response includes `artifact.saved`, `artifact.relative_path`, `artifact.sha256`, `artifact.sidecar_relative_path`, `artifact.verification_status`, and the generated filename so the console can show where the safe review artifact was stored locally and whether its hash was written.

`GET /evidence-packages/:package_id/verify` recomputes the saved package hash and compares it with the sidecar. It returns `verified` when the artifact matches and `mismatch` when the saved JSON changed after the sidecar was written.

`GET /evidence-packages/:package_id/customer-report` builds a customer-safe verification report from the saved evidence package. The report includes verification status, SHA-256 hash, sidecar path, safe run metadata, policy response, CI gate status, destination summaries, finding counts, content-hash counts, redaction-marker counts, readiness scorecard, and an explicit statement that plaintext payloads are not included. The scorecard evaluates artifact integrity, plaintext exclusion, destination control, CI gate readiness, and evidence completeness.

## Safety Notes

All endpoints require `Authorization: Bearer <session-token>` or `X-Agent-Capsule-Session: <session-token>`. Safe metadata endpoints do not decrypt raw payload sidecars for display. The live agent test creates encrypted payloads locally and returns only safe metadata. Evidence packages bundle safe metadata and policy review state only. `reveal-local` returns plaintext only when the bridge process was started with `--enable-payload-reveal`, and reveal events are appended to the local audit log.

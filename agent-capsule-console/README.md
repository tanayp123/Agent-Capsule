# Agent Capsule Console

Developer UI for running a privacy-safe AI agent demo, reviewing where data went, and exporting evidence without exposing sensitive prompts, documents, outputs, tool payloads, secrets, or user identifiers.

## Stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- shadcn/ui-style primitives
- Playwright browser tests

## Install

```bash
npm ci
```

## Develop

```bash
npm run dev -- --port 3018
```

Open:

```text
http://127.0.0.1:3018
```

## Recommended Demo

Run this from the repository root in two terminals.

Terminal 1 starts the console:

```bash
cd agent-capsule-console
npm ci
npm run dev -- --port 3018
```

Terminal 2 creates a sample trace and opens a session-scoped console URL:

```bash
source ci/python-env.sh
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli run --mode observe -- \
  python3 examples/claims-triage-python/claims_triage.py

PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli view \
  --console-url http://127.0.0.1:3018 \
  --port 3847 \
  --keep-alive \
  --no-open
```

Open the printed URL. It includes `bridge` and `session` query parameters for the localhost-only bridge.

Use the console in this order:

1. Choose a live test scenario, use the company test matrix to select the agent with the clearest risk signal, then click `Run live agent test` for one scenario or `Run scenario suite` for all built-in scenarios.
2. Review the scenario result or suite result, run ID, trace ID, span count, findings, safe execution timeline, destination findings, data classes, and policy action.
3. Choose a policy response: allow destination, allow selected fields, redact fields, require human approval, or block tool.
4. Review the policy patch preview and CI gate summary.
5. Click `Share safe proof`.
6. Review the release gate. It should explain whether the agent is blocked, ready for review, or ready for a controlled merge.
7. Click `Prepare safe trace`.
8. Click `Generate evidence package`.
9. Click `Verify saved package`.
10. Click `Build customer report`.
11. Confirm the release gate changes to `Ready for controlled merge` when scenario coverage, policy control, verified evidence, and customer proof are all present.

The live test endpoint writes encrypted payload sidecars locally, then returns only safe trace metadata and the privacy map to the browser.

## Demo Mode

Opening `http://127.0.0.1:3018` without a bridge still shows a complete guided fixture demo. In this mode, `Run live agent test` prepares the same workflow on screen but does not claim that a new encrypted trace was captured.

## Bridge URL

The CLI can generate a session-scoped console URL:

```bash
PYTHONPATH="../cli/src:../local-api/src:../sdk-python/src:../policy-engine/src" python3 -m agent_capsule_cli view \
  --console-url http://127.0.0.1:3018 \
  --port 0 \
  --no-open
```

## Build

```bash
npm run build
```

## Test

```bash
npx playwright install chromium
npm run test:ui
```

## Product Flow

- Start here: show the company workspace, ten agents, open privacy items, current run evidence, scenario-aware live testing, and a company test matrix ranked by risk, finding load, and scenario fit.
- Pick an agent: choose one of the company agents to inspect.
- See where data went: inspect destination, data classes, policy action, run ID, trace ID, span count, findings, safe execution timeline, destination findings, policy response options, patch preview, and CI gate summary.
- Export safe evidence: prepare a safe trace, review the release gate, generate an evidence package, verify the saved hash, and build the customer-ready report that includes the selected policy response.
- Local settings: advanced bridge, session-token, and local reveal controls are available but outside the primary demo path.

## Local API Bridge

The console reads `bridge` and `session` query parameters from `capsule view`. Requests use the ephemeral session token and call the localhost-only bridge for runs, timelines, privacy maps, safe trace export, replay, manifest metadata, and live agent tests. If the bridge is unavailable, the console falls back to fixtures for local UI development.

Live agent tests call:

```text
POST /live-agents/:agent_id/run
POST /live-agents/:agent_id/scenario-suite
```

The response includes:

- `run`: safe run metadata
- `test_scenario`: selected scenario name, expected result, data classes, and destination ID
- `test_result`: safe result status, finding summary, encrypted payload count, and safe-payload attestation
- `safe_trace`: redacted workflow, spans, hashes, token counts, payload sizes, and policy decisions
- `privacy_map`: destinations, data classes, findings, and policy suggestions
- `proof`: safe trace readiness, encrypted payload count, redaction markers, and finding count

The scenario suite endpoint returns a safe summary for every built-in scenario, including run ID, trace ID, result status, finding count, encrypted payload count, and safe-payload attestation. The console renders this as a compact suite panel. `Open result` loads the selected suite run into the safe data-flow view by calling the local bridge for timeline and privacy-map metadata.

The proof step can also call:

```text
POST /runs/:run_id/evidence-package
GET /evidence-packages/:package_id/verify
GET /evidence-packages/:package_id/customer-report
```

The evidence package includes safe run metadata, safe trace, privacy map, selected policy response, CI gate summary, manifest summary, content-hash counts, and redaction markers. It is designed for a teammate, security reviewer, or enterprise customer and excludes plaintext payloads.

When the console is connected to the local API bridge, generated packages are stored locally under:

```text
.agent-capsule/evidence/<package_id>.json
.agent-capsule/evidence/<package_id>.json.sha256
```

The proof step shows the filename, saved path, verification status, SHA-256 hash, sidecar path, source, CI summary, customer report status, customer finding count, and customer control count. `Verify saved package` asks the bridge to recompute the saved JSON hash and compare it with the sidecar. `Build customer report` turns the saved package into an enterprise-safe report with destination summaries, policy response, CI gate state, hash verification, excluded-data controls, readiness scorecard, and a clear statement that plaintext payloads are excluded. The report is rendered in the console so a founder or buyer can inspect the proof without opening raw JSON.

## Privacy Behavior

The console renders safe metadata by default. Raw payload reveal is disabled unless the bridge is started with `--enable-payload-reveal`; local reveal actions are audited by the bridge.

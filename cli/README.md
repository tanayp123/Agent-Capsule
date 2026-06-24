# Agent Capsule CLI

Purpose: command-line entrypoint for initialization, observe-mode runs, trace listing, safe trace export, replay, policy checks, capsule builds, local console sessions, CI checks, and confidential demos.

Phase 14 status: Guard Mode, local console bridge, signed capsule manifest build, CI/CD policy gates, and confidential demo creation are implemented.

Planned early commands:

- `capsule init`
- `capsule run --mode observe -- <command>`
- `capsule trace list`
- `capsule trace export --safe <run-id>`
- `capsule trace replay <run-id>`
- `capsule policy check`
- `capsule ci check`
- `capsule build`
- `capsule demo create`
- `capsule manifest inspect`

Tooling: Python package with Python 3.10+ during the MVP wedge unless implementation evidence requires a different split.

## Run Locally

From the repository root:

```bash
source ci/python-env.sh
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli --help
```

Initialize local configuration:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli init
```

Run an instrumented command:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli run --mode observe -- python3 examples/claims-triage-python/claims_triage.py
```

Run with Guard Mode enforcement:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli run \
  --mode guard \
  --policy fixtures/policies/restrictive-policy.json \
  -- python3 examples/claims-triage-python/claims_triage.py
```

By default, `capsule run` suppresses child process stdout and stderr so raw payloads printed by an agent are not relayed by the CLI. Use `--show-command-output` only for local debugging when command output is trusted.

List safe trace metadata:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli trace list
```

Export a shareable safe trace:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli trace export \
  --safe run_123 \
  --output safe-trace.json
```

If `--output` is omitted, the command prints the safe trace JSON to stdout.

Replay a trace structurally:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli trace replay \
  run_123 \
  --mode structural \
  --output replay.json
```

Replay with mocked model and tool results:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli trace replay \
  run_123 \
  --mode mocked \
  --output mocked-replay.json
```

Approved local plaintext replay must be explicit:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli trace replay \
  run_123 \
  --mode approved_plaintext \
  --approve-plaintext
```

Approved plaintext replay decrypts payloads locally for verification and does not serialize plaintext payload values.

Compare a replay artifact to its source trace:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli trace replay \
  run_123 \
  --compare mocked-replay.json \
  --json
```

Open the console URL without launching a browser:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli view \
  --console-url http://127.0.0.1:3018 \
  --port 0 \
  --no-open
```

`--port 0` selects an ephemeral localhost port for the local API bridge. Use `--port <number>` for a stable port, `--keep-alive` to keep the bridge running after the console session ends, `--session-token` when connecting to an already-running bridge, and `--enable-payload-reveal` only for explicit local plaintext inspection.

Evaluate a trace against policy without failing:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli policy check \
  --policy fixtures/policies/restrictive-policy.json \
  --trace fixtures/traces/crm-privacy-review.json \
  --json
```

Fail CI when undeclared high-risk egress remains:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli policy check \
  --policy fixtures/policies/restrictive-policy.json \
  --trace fixtures/traces/crm-privacy-review.json \
  --fail-on high-risk-egress
```

Run the pull request privacy and release gate:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli ci check \
  --policy agent-capsule.policy.yaml \
  --trace-dir .agent-capsule/traces \
  --manifest .agent-capsule/manifests/capsule-manifest.json \
  --release \
  --annotation-format github \
  --json
```

`capsule ci check` exits nonzero when undeclared high-risk egress remains, a destination appears in traces but not policy, high-risk data classes reach an unapproved destination, the policy is malformed or below the required version, or a release build lacks a signed manifest with a supported runtime version. The JSON output includes safe findings and annotation objects for CI systems.

Build a signed capsule manifest:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli build \
  --policy fixtures/policies/crm-policy.json \
  --output .agent-capsule/manifests/capsule-manifest.json \
  --prompt-template claim_classification=examples/claims-triage-python/claim-classification.prompt \
  --tool-schema crm.upsert_account:1.0.0:examples/claims-triage-python/crm-tool.schema.json \
  --model-provider "Example Model" \
  --model example-large \
  --required-secret MODEL_PROVIDER_API_KEY \
  --usage-meter claim_count:claim
```

Prompt templates, tool schemas, model config files, dependency lockfiles, and policies are hashed into the manifest. Prompt template plaintext and signature values are not printed by build or inspect output.

Create a confidential-like customer demo:

```bash
PYTHONPATH="cli/src:$PYTHONPATH" python3 -m agent_capsule_cli demo create \
  --customer acme-insurance \
  --mode confidential \
  --manifest .agent-capsule/manifests/capsule-manifest.json \
  --policy agent-capsule.policy.yaml \
  --trace-dir .agent-capsule/traces \
  --secret MODEL_PROVIDER_API_KEY \
  --secret CRM_API_KEY \
  --output-dir .agent-capsule/demos
```

`capsule demo create` requires a valid signed manifest, a policy matching the manifest policy hash, no undeclared high-risk egress in supplied traces, a supported runtime, verified attestation evidence, and all manifest-required secret names to be configured. The local default environment provider is `local-confidential-like`; it exercises the Confidential mode gates without claiming hosted confidential hardware.

Run tests:

```bash
bash ci/check-phase14.sh
```

## Safety Notes

- `trace list` reads safe metadata only.
- `trace export --safe` reads trace metadata and payload indexes only; it does not decrypt raw payload sidecars.
- `trace replay` defaults to structural metadata-only replay.
- `trace replay --mode approved_plaintext` fails unless `--approve-plaintext` is provided, and still does not export plaintext payload values.
- `view` starts a localhost-only API bridge by default, generates a console URL with an ephemeral session token, and shuts the bridge down when the console ends the session unless `--keep-alive` is set.
- The local API bridge returns safe trace metadata, privacy maps, policy decisions, and replay artifacts without decrypting raw payload sidecars.
- `view --enable-payload-reveal` is required before the local reveal endpoint can decrypt a payload, and reveal attempts are written to the local audit log.
- `manifest inspect` prints safe manifest metadata and does not print signature values.
- `build` creates a signed manifest and build report with hashes for dependencies, prompts, tools, model configuration, and policy.
- `policy check` prints policy findings and suggestions from safe metadata only.
- `ci check` prints safe policy and release findings only; it does not print payload plaintext or manifest signature values.
- `demo create` releases only secret names after runtime verification and writes safe customer verification, vendor telemetry, attestation, and support artifacts without secret values or manifest signature values.
- `run --mode guard` fails closed when policy cannot load, blocks disallowed supported calls, and records safe policy decisions without printing raw payloads.
- The CLI does not decrypt raw payload sidecars for trace listing, safe trace export, structural replay, mocked replay, redacted replay, manifest inspection, policy checks, CI checks, or demo creation.

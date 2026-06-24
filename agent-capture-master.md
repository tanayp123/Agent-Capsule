# Agent Capsule Master Guide

File name: `agent-capture-master.md`  
Product name: Agent Capsule  
Audience: founders, developers, security reviewers, solutions teams, and enterprise platform teams  
Status: based on the implemented repository through Phase 15

## Table Of Contents

1. First-Time Product Walkthrough With Sample Example
2. Founder Explanation For A Non-Technical Audience
3. Five Paying Customer Personas And Workflows
4. Appendix: Commands, Artifacts, And Safety Rules

## 1. First-Time Product Walkthrough With Sample Example

### 1.1 What Agent Capsule Does

Agent Capsule helps teams build, debug, review, and demonstrate AI agents without turning private prompts, documents, model outputs, tool payloads, secrets, or user identifiers into ordinary logs.

The product has four practical jobs:

- Capture safe execution metadata from an agent run.
- Store sensitive payload material locally and encrypted.
- Show data-flow and policy evidence so developers can review where data goes.
- Produce safe traces, CI findings, signed manifests, and confidential-demo artifacts that can be shared without exposing plaintext customer data.

Agent Capsule is not only a monitoring tool. It is a workflow that moves an AI agent from local debugging to enterprise review:

```text
Developer run
    |
    v
Observe mode captures safe metadata
    |
    v
Encrypted local trace store
    |
    +--> Agent Capsule Console for local inspection
    |
    +--> Privacy map and policy check
    |
    +--> Safe trace for teammate debugging
    |
    +--> Replay for reproduction
    |
    +--> Signed manifest for release evidence
    |
    +--> Confidential-like customer demo artifacts
    |
    v
CI blocks undeclared high-risk egress before merge
```

### 1.2 Product Pieces You Will Use

```text
+---------------------------+----------------------------------------------+
| Piece                     | What it does                                  |
+---------------------------+----------------------------------------------+
| Python SDK                | Instruments a Python agent run.               |
| CLI                       | Runs observe/guard flows, exports traces,     |
|                           | checks policy, builds manifests, opens UI.    |
| Encrypted trace store     | Keeps sensitive local payload sidecars        |
|                           | separated from safe metadata.                 |
| Policy engine             | Decides allow, allow fields, redact, require  |
|                           | approval, warn, or block.                     |
| Agent Capsule Console     | Local UI for runs, timelines, data flow,      |
|                           | privacy map, replay, safe export, manifests. |
| CI gate                   | Fails pull requests with undeclared high-risk |
|                           | egress or release evidence gaps.              |
| Capsule manifest          | Signed release evidence for the agent.        |
| Confidential demo flow    | Builds safe customer proof-of-concept         |
|                           | artifacts after verification gates pass.      |
| Product website           | Enterprise-facing product site.               |
+---------------------------+----------------------------------------------+
```

### 1.3 Before You Start

Recommended local setup:

- Python 3.10 or newer.
- Node.js 20 or newer for the console and product website.
- Git.
- Docker if you want container-oriented release validation later.
- No GPU is required unless your own agent uses local models.
- No TPM, Secure Enclave, or local HSM is required for the MVP local workflow.

Hardware summary:

```text
+-------------------------------+-----------------------------+
| Workflow                      | Special hardware required?  |
+-------------------------------+-----------------------------+
| Observe mode                  | No                          |
| Guard mode                    | No                          |
| Encrypted local traces        | No                          |
| Console UI                    | No                          |
| Safe trace export             | No                          |
| Replay                        | No                          |
| CI policy check               | No                          |
| Local confidential-like demo  | No                          |
| Hosted confidential demo      | Yes, cloud confidential     |
|                               | computing infrastructure    |
+-------------------------------+-----------------------------+
```

### 1.4 Sample Scenario

The repository includes a sample Python agent called `claims-triage`. It imitates a claims workflow that:

- Calls a model provider.
- Calls a CRM tool.
- Classifies data fields such as email, account notes, policy number, document text, and incident details.
- Produces trace metadata that can be reviewed safely.

The sample is useful because it shows the core enterprise privacy problem:

```text
The team adds a CRM tool.
The agent sends email and account notes to the CRM.
The destination is not declared in policy.
Agent Capsule detects the data flow.
The developer must update policy or block the tool before merge.
```

### 1.5 Step 1: Open The Repository

From a terminal:

```bash
cd "/Users/tanayparikh/Documents/Agent Capsule"
```

Confirm the main files exist:

```bash
ls
```

Expected important entries:

```text
PRD.md
agent.md
README.md
cli/
sdk-python/
policy-engine/
trace-store/
local-api/
agent-capsule-console/
agent-capsule-website/
examples/
fixtures/
docs/
ci/
```

### 1.6 Step 2: Load The Local Python Environment

Run:

```bash
source ci/python-env.sh
```

Then expose the CLI package:

```bash
export PYTHONPATH="$PWD/cli/src:$PWD/sdk-python/src:$PWD/policy-engine/src:$PWD/trace-store/src:$PWD/local-api/src:$PYTHONPATH"
```

Check the CLI:

```bash
python3 -m agent_capsule_cli --help
```

Mock terminal:

```text
$ python3 -m agent_capsule_cli --help

Usage: agent_capsule_cli [command] [options]

Commands:
  init
  run
  trace list
  trace export
  trace replay
  policy check
  ci check
  build
  demo create
  manifest inspect
  view
```

### 1.7 Step 3: Initialize Agent Capsule

Run:

```bash
python3 -m agent_capsule_cli init
```

What this means:

- Creates local Agent Capsule configuration.
- Prepares a conventional `.agent-capsule/` workspace.
- Establishes where traces, manifests, reports, and demo artifacts can live.

Expected local shape:

```text
.agent-capsule/
  traces/
  manifests/
  demos/
```

### 1.8 Step 4: Run The Sample Agent In Observe Mode

Observe mode records what happened, but it does not block execution.

Run:

```bash
python3 -m agent_capsule_cli run \
  --mode observe \
  -- python3 examples/claims-triage-python/claims_triage.py
```

Important privacy behavior:

- The CLI suppresses child process stdout and stderr by default.
- This prevents accidental raw prompt, document, or payload output from being relayed into logs.
- Use `--show-command-output` only when you trust the local command output.

Mock terminal:

```text
$ python3 -m agent_capsule_cli run --mode observe -- python3 examples/claims-triage-python/claims_triage.py

Agent Capsule run started
mode: observe
agent: claims-triage
trace store: .agent-capsule/traces

Run completed
run_id: run_01H_SAFE_EXAMPLE
trace_id: trc_01H_SAFE_EXAMPLE
safe metadata written
encrypted payload sidecars written locally
```

What Agent Capsule captures:

```text
+--------------------------+---------------------------------------------+
| Captured metadata        | Example                                     |
+--------------------------+---------------------------------------------+
| Run ID                   | run_01H_SAFE_EXAMPLE                        |
| Trace ID                 | trc_01H_SAFE_EXAMPLE                        |
| Span ID                  | spn_model_001                               |
| Component type           | model_call, tool_call                       |
| Component name           | classify-claim, crm.upsert_account         |
| Runtime                  | python 3.10.x                               |
| SDK version              | 0.1.0                                       |
| Destination              | api.model.example, api.crm.example          |
| Data classes             | email, account_notes, document_text         |
| Payload size             | byte count only                             |
| Token count              | count only                                  |
| Content hash             | sha256 hash                                 |
| Policy decision          | warn, redact, block, etc.                   |
| Redaction markers        | hashed:email, redacted:account_notes        |
+--------------------------+---------------------------------------------+
```

What it avoids exposing by default:

```text
+----------------------------------+
| Not shown in ordinary output      |
+----------------------------------+
| Prompt plaintext                  |
| Document plaintext                |
| Model output plaintext            |
| Tool payload plaintext            |
| Secret values                     |
| User identifiers                  |
| Manifest signature values         |
+----------------------------------+
```

### 1.9 Step 5: List Safe Trace Metadata

Run:

```bash
python3 -m agent_capsule_cli trace list
```

Mock terminal:

```text
$ python3 -m agent_capsule_cli trace list

+----------------------+----------------------+----------+---------------------+
| run_id               | agent                | mode     | created_at          |
+----------------------+----------------------+----------+---------------------+
| run_01H_SAFE_EXAMPLE | claims-triage        | observe  | 2026-06-23 18:25:00 |
+----------------------+----------------------+----------+---------------------+

Safe metadata only. Raw payloads were not decrypted.
```

### 1.10 Step 6: Understand The Trace Store

The trace store separates metadata from sensitive payloads.

```text
.agent-capsule/traces/
  metadata/
    trc_01H_SAFE_EXAMPLE.json
  payloads/
    trc_01H_SAFE_EXAMPLE/
      encrypted_payload_001.bin
      encrypted_payload_002.bin
```

Conceptual model:

```text
+---------------------------------------------+
| Safe metadata JSON                           |
|                                             |
| run id                                      |
| span names                                  |
| destination domains                         |
| data classes                                |
| payload sizes                               |
| token counts                                |
| hashes                                      |
| policy decisions                            |
| redaction markers                           |
+---------------------------------------------+
                    |
                    | references by hash or payload id
                    v
+---------------------------------------------+
| Encrypted local payload sidecars             |
|                                             |
| plaintext is not printed                     |
| plaintext is not exported in safe traces     |
| reveal requires explicit local authorization |
+---------------------------------------------+
```

### 1.11 Step 7: Open Agent Capsule Console

The console is the local UI for encrypted traces, data-flow visibility, privacy review, replay comparison, safe trace export, and manifest inspection.

Terminal A:

```bash
cd "/Users/tanayparikh/Documents/Agent Capsule/agent-capsule-console"
npm ci
npm run dev -- --port 3018
```

Terminal B:

```bash
cd "/Users/tanayparikh/Documents/Agent Capsule"
source ci/python-env.sh
export PYTHONPATH="$PWD/cli/src:$PWD/local-api/src:$PWD/sdk-python/src:$PWD/policy-engine/src:$PWD/trace-store/src:$PYTHONPATH"

python3 -m agent_capsule_cli view \
  --console-url http://127.0.0.1:3018 \
  --port 0 \
  --no-open
```

The CLI prints a local console URL with a bridge address and session token.

Mock terminal:

```text
Local API bridge started
bridge: http://127.0.0.1:49321
session: sess_local_redacted

Open:
http://127.0.0.1:3018/?bridge=http%3A%2F%2F127.0.0.1%3A49321&session=sess_local_redacted
```

Open that URL in the browser.

### 1.12 Mock Screen: Console Runs Dashboard

```text
+----------------------------------------------------------------------------+
| Agent Capsule Console                                                       |
+----------------------------------------------------------------------------+
| Runs | Timeline | Data Flow | Privacy Map | Replay | Manifest | Settings   |
+----------------------------------------------------------------------------+
| Recent Runs                                                                 |
|                                                                            |
| +----------------------+--------------+----------+----------+-------------+ |
| | Run ID               | Agent        | Mode     | Status   | Decisions   | |
| +----------------------+--------------+----------+----------+-------------+ |
| | run_01H_SAFE_EXAMPLE | claims-triage| observe  | ok       | 2 warnings  | |
| | run_failed_model_001 | claims-triage| observe  | failed   | 1 warning   | |
| +----------------------+--------------+----------+----------+-------------+ |
|                                                                            |
| Payload reveal: disabled                                                    |
| Bridge: localhost only                                                      |
| Session: active                                                             |
+----------------------------------------------------------------------------+
```

What to look for:

- Run list shows safe metadata only.
- You can see status, timing, decisions, and destinations.
- You do not see raw prompts, documents, model outputs, tool payloads, secrets, or user identifiers.

### 1.13 Mock Screen: Trace Timeline

```text
+----------------------------------------------------------------------------+
| Trace Timeline: run_01H_SAFE_EXAMPLE                                        |
+----------------------------------------------------------------------------+
| Time       Component             Type        Destination        Decision     |
+----------------------------------------------------------------------------+
| 00:00.000  claims-triage          workflow    local              not eval     |
| 00:00.118  classify-claim         model       api.model.example  allow        |
| 00:00.746  crm.upsert_account     tool        api.crm.example    warn         |
+----------------------------------------------------------------------------+
| Selected span                                                               |
|                                                                            |
| span_id: spn_crm_001                                                        |
| data_classes: email, account_notes                                          |
| payload_size_bytes: 1120                                                    |
| content_hash: sha256:4444...4444                                            |
| redaction_markers: hashed:email, hashed:account_notes                       |
| plaintext: not displayed                                                    |
+----------------------------------------------------------------------------+
```

### 1.14 Step 8: Review Data-Flow Visibility

The data-flow view answers:

- Which systems did the agent call?
- What classes of data moved?
- Which destination received them?
- Were those destinations declared in policy?
- Would CI block this change?

Mock screen:

```text
+----------------------------------------------------------------------------+
| Data Flow                                                                   |
+----------------------------------------------------------------------------+
|                                                                            |
| [claims-triage agent]                                                       |
|       |                                                                    |
|       | prompt_content, document_text                                       |
|       v                                                                    |
| [api.model.example]             declared: yes     risk: medium             |
|                                                                            |
| [claims-triage agent]                                                       |
|       |                                                                    |
|       | email, account_notes                                                |
|       v                                                                    |
| [api.crm.example]               declared: no      risk: high               |
|                                                                            |
+----------------------------------------------------------------------------+
| Finding                                                                    |
| undeclared_high_risk_egress: api.crm.example receives email, account_notes |
+----------------------------------------------------------------------------+
```

### 1.15 Step 9: Run A Policy Check

Use the included CRM privacy-review fixture:

```bash
python3 -m agent_capsule_cli policy check \
  --policy fixtures/policies/restrictive-policy.json \
  --trace fixtures/traces/crm-privacy-review.json \
  --json
```

The restrictive policy has no declared destinations:

```json
{
  "version": 1,
  "agent": {
    "name": "claims-triage",
    "owner": "platform-team"
  },
  "destinations": {},
  "defaults": {
    "undeclared_high_risk_egress": "block",
    "undeclared_destination": "warn",
    "secrets": "block"
  }
}
```

Expected result:

```text
Destination api.crm.example observed.
Observed data classes: email, account_notes.
Destination is not declared in policy.
Risk: high.
Suggested actions:
  allow destination
  allow selected fields
  redact fields
  require human approval
  block tool
```

To make it fail like CI:

```bash
python3 -m agent_capsule_cli policy check \
  --policy fixtures/policies/restrictive-policy.json \
  --trace fixtures/traces/crm-privacy-review.json \
  --fail-on high-risk-egress
```

Mock terminal:

```text
$ capsule policy check --fail-on high-risk-egress

FAIL
finding: undeclared_high_risk_egress
destination: crm
domain: api.crm.example
data_classes: account_notes, email
risk: high

Action required before merge.
```

### 1.16 Step 10: Choose A Policy Action

Agent Capsule turns privacy review into a normal engineering decision. The developer or reviewer chooses one action.

#### Option A: Allow The Destination

Use when the destination is approved to receive all observed data classes.

```json
{
  "destinations": {
    "crm": {
      "type": "external_tool",
      "domain": "api.crm.example",
      "risk": "high",
      "allowed_data": [
        "email",
        "account_notes"
      ],
      "redact": [],
      "require_approval": []
    }
  }
}
```

When to use:

- The CRM is contractually approved.
- The data classes are expected.
- Security and compliance have signed off.

#### Option B: Allow Only Selected Fields

Use when the destination should receive only a subset of the payload.

```json
{
  "destinations": {
    "crm": {
      "type": "external_tool",
      "domain": "api.crm.example",
      "risk": "high",
      "allowed_data": [
        "account_id",
        "support_tier"
      ],
      "redact": [],
      "require_approval": []
    }
  }
}
```

Expected behavior:

```text
Allowed fields proceed.
Other classified fields are removed before egress.
Decision recorded as allow_fields.
```

#### Option C: Redact Specified Fields

Use when the destination is approved but sensitive fields should not leave.

```json
{
  "destinations": {
    "crm": {
      "type": "external_tool",
      "domain": "api.crm.example",
      "risk": "high",
      "allowed_data": [
        "account_id",
        "support_tier"
      ],
      "redact": [
        "email",
        "account_notes"
      ],
      "require_approval": []
    }
  }
}
```

Expected behavior:

```text
email -> redacted
account_notes -> redacted
policy_decision.action -> redact
trace keeps redaction markers and hashes
```

#### Option D: Require Human Approval

Use when a human should approve the call before data leaves.

```json
{
  "destinations": {
    "crm": {
      "type": "external_tool",
      "domain": "api.crm.example",
      "risk": "high",
      "allowed_data": [
        "account_id"
      ],
      "redact": [
        "email"
      ],
      "require_approval": [
        "account_notes",
        "medical_information"
      ]
    }
  }
}
```

Expected behavior:

```text
Execution pauses before egress.
Approval handler receives safe request metadata only.
Plaintext payload is not sent to the approval handler.
Decision is recorded in the trace.
```

#### Option E: Block The Tool

Use when the tool should not be called.

```json
{
  "defaults": {
    "undeclared_high_risk_egress": "block",
    "undeclared_destination": "warn",
    "secrets": "block"
  }
}
```

Expected behavior in Guard Mode:

```text
The call is prevented.
Trace records a block decision.
No supported egress occurs.
```

### 1.17 Step 11: Run Guard Mode

Guard Mode enforces policy before supported model and tool calls leave the agent boundary.

Run:

```bash
python3 -m agent_capsule_cli run \
  --mode guard \
  --policy fixtures/policies/restrictive-policy.json \
  -- python3 examples/claims-triage-python/claims_triage.py
```

Expected outcome with restrictive policy:

```text
Guard Mode loads policy.
Policy has no approved CRM destination.
CRM egress is high risk.
Call is blocked before supported egress.
Safe trace metadata is still written.
```

Mock terminal:

```text
Agent Capsule run started
mode: guard
policy: fixtures/policies/restrictive-policy.json

Policy decision:
  destination: crm
  action: block
  reason: undeclared high-risk egress
  fields: account_notes, email

Run stopped by Guard Mode.
safe metadata written
plaintext not printed
```

### 1.18 Step 12: Export A Safe Trace For A Teammate

Safe traces help a teammate debug the failure without seeing private payloads.

Run:

```bash
python3 -m agent_capsule_cli trace export \
  --safe run_01H_SAFE_EXAMPLE \
  --output safe-trace.json
```

Safe trace contains:

```text
+-----------------------------------+
| Safe trace keeps                  |
+-----------------------------------+
| workflow structure                |
| timing                            |
| component versions                |
| error summaries                   |
| token counts                      |
| payload sizes                     |
| policy decisions                  |
| content hashes                    |
| redaction markers                 |
+-----------------------------------+
```

Safe trace removes or hashes:

```text
+-----------------------------------+
| Safe trace does not include       |
+-----------------------------------+
| prompt plaintext                  |
| document plaintext                |
| model output plaintext            |
| tool payload plaintext            |
| secret values                     |
| user identifiers                  |
+-----------------------------------+
```

Mock screen:

```text
+----------------------------------------------------------------------------+
| Safe Trace Export                                                           |
+----------------------------------------------------------------------------+
| Run: run_01H_SAFE_EXAMPLE                                                   |
| Profile: team_debug                                                         |
|                                                                            |
| Included                                                                    |
|   workflow structure                                                        |
|   component versions                                                        |
|   timing and errors                                                         |
|   token counts and payload sizes                                            |
|   policy decisions                                                          |
|   content hashes                                                            |
|   redaction markers                                                         |
|                                                                            |
| Excluded                                                                    |
|   prompt content                                                            |
|   document text                                                             |
|   model outputs                                                             |
|   tool payloads                                                             |
|   secrets                                                                   |
|   user identifiers                                                          |
|                                                                            |
| Result: safe-trace.json                                                     |
+----------------------------------------------------------------------------+
```

### 1.19 Step 13: Replay The Run

Replay is used to reproduce a workflow shape without reusing sensitive plaintext by default.

Structural replay:

```bash
python3 -m agent_capsule_cli trace replay \
  run_01H_SAFE_EXAMPLE \
  --mode structural \
  --output replay.json
```

Mocked replay:

```bash
python3 -m agent_capsule_cli trace replay \
  run_01H_SAFE_EXAMPLE \
  --mode mocked \
  --output mocked-replay.json
```

Compare replay to source trace:

```bash
python3 -m agent_capsule_cli trace replay \
  run_01H_SAFE_EXAMPLE \
  --compare mocked-replay.json \
  --json
```

Approved plaintext replay exists only for explicit local verification:

```bash
python3 -m agent_capsule_cli trace replay \
  run_01H_SAFE_EXAMPLE \
  --mode approved_plaintext \
  --approve-plaintext
```

Important:

```text
Approved plaintext replay decrypts locally for verification.
It still does not serialize plaintext payload values into exported artifacts.
```

### 1.20 Step 14: Build A Signed Capsule Manifest

The manifest is the release evidence package. It records what the agent is, which prompts and tools are present, which model configuration is declared, which secrets are required, and which policy hash applies.

Run:

```bash
python3 -m agent_capsule_cli build \
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

Manifest evidence includes:

```text
+---------------------------+----------------------------------------------+
| Evidence                  | Safe behavior                                |
+---------------------------+----------------------------------------------+
| Prompt template           | hash only, not plaintext                     |
| Tool schema               | hash and version                             |
| Model configuration       | provider and model metadata                  |
| Policy                    | policy hash and version                      |
| Required secrets          | secret names only, not values                |
| Dependencies              | lockfile or dependency hashes                |
| Usage meters              | declared billing or metering dimensions      |
| Signature                 | used for verification, not printed in inspect|
+---------------------------+----------------------------------------------+
```

Mock manifest inspection:

```text
+----------------------------------------------------------------------------+
| Capsule Manifest                                                            |
+----------------------------------------------------------------------------+
| agent: claims-triage                                                        |
| version: 0.1.0                                                              |
| runtime: python 3.10                                                        |
| policy_version: 1                                                           |
| policy_hash: sha256:...                                                     |
| prompt_templates: claim_classification -> sha256:...                        |
| tools: crm.upsert_account:1.0.0 -> sha256:...                               |
| required_secrets: MODEL_PROVIDER_API_KEY, CRM_API_KEY                       |
| signature: present                                                          |
| signature_value: hidden                                                     |
+----------------------------------------------------------------------------+
```

### 1.21 Step 15: Run The CI Privacy Gate

CI should fail when privacy drift remains.

Example command:

```bash
python3 -m agent_capsule_cli ci check \
  --policy fixtures/policies/crm-policy.json \
  --trace fixtures/traces/crm-privacy-review.json \
  --manifest .agent-capsule/manifests/claims-triage-manifest.json \
  --release \
  --annotation-format github \
  --json
```

Pull request workflow:

```text
Developer opens PR
    |
    v
CI runs capsule ci check
    |
    +--> policy malformed? fail
    +--> destination undeclared? fail or warn based on risk
    +--> high-risk data reaches unapproved destination? fail
    +--> release manifest missing? fail
    +--> unsupported runtime? fail
    |
    v
PR can merge only after findings are resolved
```

Mock CI screen:

```text
+----------------------------------------------------------------------------+
| Pull Request: Add CRM integration                                           |
+----------------------------------------------------------------------------+
| Checks                                                                     |
|   unit tests                                    passed                      |
|   schema validation                             passed                      |
|   capsule ci check                             failed                      |
|                                                                            |
| Finding                                                                    |
|   undeclared_high_risk_egress                                               |
|   destination: api.crm.example                                              |
|   data classes: email, account_notes                                        |
|   action: declare destination, redact fields, require approval, or block    |
+----------------------------------------------------------------------------+
```

### 1.22 Step 16: Create A Confidential-Like Customer Demo

This local workflow validates the Confidential mode gates. It does not claim that your laptop is hosted confidential-computing hardware.

Run:

```bash
python3 -m agent_capsule_cli demo create \
  --customer acme-insurance \
  --mode confidential \
  --manifest .agent-capsule/manifests/claims-triage-manifest.json \
  --policy fixtures/policies/crm-policy.json \
  --trace-dir .agent-capsule/traces \
  --secret MODEL_PROVIDER_API_KEY \
  --secret CRM_API_KEY \
  --output-dir .agent-capsule/demos
```

The command checks:

```text
+-----------------------------------------+
| Confidential demo gate                  |
+-----------------------------------------+
| signed manifest exists                  |
| manifest signature is valid enough      |
| runtime is supported                    |
| policy hash matches manifest            |
| destinations are declared               |
| no undeclared high-risk egress remains  |
| attestation evidence verifies           |
| required secret names are configured    |
+-----------------------------------------+
```

Artifacts:

```text
.agent-capsule/demos/acme-insurance/
  attestation-result.json
  customer-verification.html
  vendor-telemetry.json
  support-bundle.json
```

Mock customer verification page:

```text
+----------------------------------------------------------------------------+
| Agent Capsule Customer Verification                                         |
+----------------------------------------------------------------------------+
| Customer: acme-insurance                                                    |
| Capsule: claims-triage                                                      |
| Manifest: signed                                                            |
| Attestation: verified                                                       |
| Runtime: python 3.10                                                        |
| Policy version: 1                                                           |
|                                                                            |
| Approved destinations                                                       |
|   api.model.example       model provider        medium risk                 |
|   api.crm.example         CRM tool              high risk                   |
|                                                                            |
| Data handling                                                               |
|   email                  redacted for CRM                                   |
|   account_notes          redacted for CRM                                   |
|   medical_information    requires approval                                 |
|                                                                            |
| Secret release                                                              |
|   MODEL_PROVIDER_API_KEY configured, value hidden                           |
|   CRM_API_KEY configured, value hidden                                      |
+----------------------------------------------------------------------------+
```

### 1.23 Step 17: Use The Product Website

The product website is separate from the console. It is designed for enterprise-facing explanation and sales conversations.

Run:

```bash
cd "/Users/tanayparikh/Documents/Agent Capsule/agent-capsule-website"
npm ci
npm run dev -- --port 3020
```

Open:

```text
http://127.0.0.1:3020
```

What the website explains:

- Private debugging with encrypted traces.
- Policy review and data-flow visibility.
- Safe trace collaboration.
- Confidential customer demonstration.
- Multi-language SDK support.
- Hardware requirements.
- Enterprise evidence artifacts.

### 1.24 First-Time Workflow Summary

Use this as the one-page operating flow:

```text
+-----------------------------------------------------------------------------+
| First-Time Agent Capsule Workflow                                            |
+-----------------------------------------------------------------------------+
| 1. Initialize Agent Capsule                                                  |
|      capsule init                                                            |
|                                                                             |
| 2. Run agent in Observe mode                                                 |
|      capsule run --mode observe -- python3 examples/...                      |
|                                                                             |
| 3. List safe traces                                                          |
|      capsule trace list                                                      |
|                                                                             |
| 4. Open Console                                                              |
|      npm run dev -- --port 3018                                              |
|      capsule view --console-url http://127.0.0.1:3018 --port 0 --no-open    |
|                                                                             |
| 5. Review data flow and privacy map                                          |
|      detect destinations and data classes                                    |
|                                                                             |
| 6. Update policy                                                             |
|      allow, allow fields, redact, require approval, or block                 |
|                                                                             |
| 7. Run Guard Mode                                                            |
|      capsule run --mode guard --policy policy.json -- command                |
|                                                                             |
| 8. Export safe trace                                                         |
|      capsule trace export --safe <run_id> --output safe-trace.json           |
|                                                                             |
| 9. Replay                                                                    |
|      capsule trace replay <run_id> --mode mocked                             |
|                                                                             |
| 10. Build signed manifest                                                    |
|      capsule build --policy policy.json --output capsule-manifest.json       |
|                                                                             |
| 11. Add CI gate                                                              |
|      capsule ci check --policy policy.json --trace-dir .agent-capsule/traces |
|                                                                             |
| 12. Create confidential-like demo                                            |
|      capsule demo create --customer <name> --mode confidential               |
+-----------------------------------------------------------------------------+
```

### 1.25 Common First-Time Troubleshooting

```text
+------------------------------------+-----------------------------------------+
| Problem                            | What to do                              |
+------------------------------------+-----------------------------------------+
| CLI module not found               | Re-export PYTHONPATH from repo root.    |
| Console cannot reach bridge        | Run capsule view again and use the URL  |
|                                    | containing bridge and session values.   |
| Policy check fails                 | Review destination and data classes.    |
| Guard Mode blocks the run          | This is expected for undeclared high-   |
|                                    | risk egress. Update policy or block.    |
| Safe trace lacks raw payload       | Expected. Safe traces intentionally     |
|                                    | omit plaintext sensitive content.       |
| Demo create fails on secrets       | Pass required secret names, not values. |
| Hosted confidential demo needed    | Use a supported cloud confidential      |
|                                    | computing environment and attestation.  |
+------------------------------------+-----------------------------------------+
```

## 2. Founder Explanation For A Non-Technical Audience

### 2.1 The Short Version

Agent Capsule helps AI companies prove what their agent does with customer data.

Today, when an AI agent makes mistakes or sends data to different tools, teams often debug using logs that contain sensitive customer information. That creates risk. It also makes enterprise sales harder because customers ask where their data goes, which models see it, and how the vendor can support the agent without seeing private data.

Agent Capsule gives the vendor a privacy-safe way to answer:

```text
What did the agent do?
Where did data go?
Which data classes left the agent?
Was that allowed by policy?
Can we debug the failure without seeing customer data?
Can the customer verify what version and policy are running?
```

### 2.2 Simple Analogy

Imagine a delivery company moving sealed packages.

Traditional logs are like opening every package and photocopying the contents so the company can troubleshoot delivery problems.

Agent Capsule is like keeping:

- The route.
- The timestamps.
- The package weight.
- The destination.
- The approval stamp.
- A tamper-evident package fingerprint.

The company can diagnose the delivery route without reading what is inside the package.

### 2.3 Why This Matters For AI Agents

AI agents are not simple chatbots. They often:

- Read documents.
- Call models.
- Search databases.
- Use CRM systems.
- Send emails.
- Make API calls.
- Ask humans for approval.
- Handle regulated or confidential data.

That means every agent run creates an evidence problem:

```text
The customer wants productivity.
The vendor wants debugging visibility.
The enterprise wants privacy and control.
```

Agent Capsule gives all three sides a shared evidence layer.

### 2.4 The Business Problem

AI startups selling to enterprises hear questions like:

- Can your agent run in our environment?
- Can we see exactly where our data goes?
- Can you prove which model provider receives which data?
- Can you support us without seeing our private documents?
- Can we approve or block new tools?
- Can policy changes be reviewed in version control?
- Can CI stop unsafe changes before they ship?

Without Agent Capsule, the startup often has to build custom logging, custom security review documents, custom deployment evidence, and custom support bundles for each enterprise customer.

Agent Capsule turns that into a repeatable product workflow.

### 2.5 What The Product Is In Business Terms

Agent Capsule is a trust and evidence layer for AI agents.

It includes:

```text
+-------------------------+-----------------------------------------------+
| Product capability      | Business meaning                              |
+-------------------------+-----------------------------------------------+
| Private debugging       | Engineers can solve failures without dumping  |
|                         | customer data into logs.                      |
| Data-flow visibility    | Teams can show where customer data goes.      |
| Policy enforcement      | Risky data movement can be blocked, redacted, |
|                         | or sent for approval.                         |
| Safe traces             | Teammates and support teams can diagnose      |
|                         | problems without private payloads.            |
| CI privacy gate         | Unsafe changes are caught before merge.       |
| Signed manifest         | Customers can verify version, policy, tools,  |
|                         | models, dependencies, and secrets needed.     |
| Confidential demo       | Sales teams can run proof-of-concept flows    |
|                         | with safe customer and vendor artifacts.      |
+-------------------------+-----------------------------------------------+
```

### 2.6 Before And After

Before Agent Capsule:

```text
Developer: "The agent failed. I need the prompt, documents, model output, and tool payload."
Security:  "Do not share that data."
Founder:   "The customer needs answers this week."
Result:    Slow manual review, risky logs, custom one-off evidence.
```

After Agent Capsule:

```text
Developer: "I can see the workflow, timing, destinations, token counts, payload sizes, policy decisions, and hashes."
Security:  "No plaintext private payloads are in the safe trace."
Founder:   "We can show the customer a repeatable evidence package."
Result:    Faster debugging, safer review, stronger enterprise sales motion.
```

### 2.7 Why Customers Pay

Customers pay because Agent Capsule reduces:

- Enterprise sales friction.
- Security review delays.
- Engineering time spent building custom private debugging tools.
- Risk of leaking customer data through logs.
- Risk of shipping undeclared data egress.
- Support burden when production-like runs fail.
- Need for a separate enterprise-only codebase.

Customers also pay because it can become part of their compliance and procurement story:

```text
"We do not ask you to blindly trust our AI agent.
We can show you what it can access, where data can go, what policy applies,
which version is running, and how support works without exposing your data."
```

### 2.8 What A Founder Should Say In A Customer Meeting

Use this plain-language explanation:

```text
Agent Capsule is our privacy evidence layer for AI agents.

It lets our engineers debug the agent without putting your private data into logs.
It shows which systems the agent called and which kinds of data went there.
It lets us enforce policy so new high-risk data flows cannot silently ship.
It creates safe traces for support and signed evidence for deployment review.

For a private proof of concept, we can provide a customer verification page
showing the agent version, policy, approved destinations, attestation status,
required secret names, and safe telemetry, without exposing your data.
```

### 2.9 What Agent Capsule Is Not

Agent Capsule should not be oversold.

It is not:

- A guarantee that an AI model will always behave correctly.
- A guarantee that prompt injection is impossible.
- A replacement for application security review.
- A replacement for cloud identity and access management.
- A hosted confidential-computing environment by itself.
- A reason to send unnecessary data to a model or tool.

It is:

- A way to observe, control, and prove agent data movement.
- A way to make privacy behavior part of engineering workflow.
- A way to create safe artifacts for debugging, review, and customer proof.

### 2.10 Founder Demo Script

A simple founder-friendly demo can take 10 minutes.

```text
Minute 1:
  Show the problem. AI agents call models and tools. Logs can expose private data.

Minute 2:
  Run the sample agent in Observe mode.

Minute 3:
  Open the Console. Show trace timeline and data-flow view.

Minute 4:
  Show that email and account notes went to a CRM destination.

Minute 5:
  Show policy check failing because the destination was undeclared.

Minute 6:
  Choose a policy action: redact email and account notes, require approval for medical data.

Minute 7:
  Run Guard Mode. Show policy enforcement before egress.

Minute 8:
  Export a safe trace. Show that it has useful debugging metadata but no plaintext payload.

Minute 9:
  Build a signed manifest. Show prompts and tools are represented by hashes.

Minute 10:
  Create a confidential-like demo. Show customer verification and safe vendor telemetry.
```

### 2.11 Founder FAQ

```text
Q: Is this mainly for developers or enterprise buyers?
A: It starts with developers because private debugging is a daily pain. It expands
   into enterprise buying because the same traces, policies, and manifests become
   sales and deployment evidence.

Q: Does this require special hardware?
A: Local development does not. Hosted confidential demos and customer-cloud
   deployments require supported cloud confidential-computing infrastructure.

Q: What is the wedge?
A: Private-by-default debugging and data-flow visibility for AI agents.

Q: What is the enterprise expansion?
A: Attested deployment evidence, policy governance, private support, release
   verification, and eventually licensing and metering.

Q: Why not just use a normal observability product?
A: Normal observability often assumes logs and traces can be uploaded. Agent
   Capsule assumes agent payloads may be private and should stay local or be
   represented as safe metadata.

Q: How does this help sales?
A: It gives the startup a concrete answer to security questionnaires and private
   proof-of-concept requirements.
```

## 3. Five Paying Customer Personas And Workflows

### Persona 1: AI Startup CTO Selling To Enterprises

Profile:

```text
Name: Maya
Company: 30-person AI claims automation startup
Buyer type: Startup CTO and budget owner
Main pressure: Close enterprise deals without building one-off private deployments
```

Why Maya pays:

- Enterprise prospects ask where data goes.
- The startup needs a credible privacy story before procurement.
- Engineers are losing time preparing custom security evidence.
- The CTO wants one agent codebase for development, demos, and enterprise deployment.

Workflow:

```text
1. Add Agent Capsule SDK to the Python claims agent.
2. Run local development flows in Observe mode.
3. Use Console to review model calls, tool calls, destinations, and data classes.
4. Add a policy file to version control.
5. Run Guard Mode for high-risk flows.
6. Add capsule ci check to pull request CI.
7. Build a signed capsule manifest for each release candidate.
8. Run capsule demo create for enterprise proof of concept.
9. Share customer-verification.html with the prospect.
10. Use safe vendor telemetry for support during evaluation.
```

Persona workflow diagram:

```text
Maya's team builds feature
    |
    v
Observe mode detects new destination
    |
    v
Policy review in PR
    |
    +--> approved and declared
    |       |
    |       v
    |   CI passes
    |
    +--> undeclared high-risk egress
            |
            v
        CI fails until fixed
```

Success metrics:

- Security questionnaire turnaround drops from weeks to days.
- New customer demos use a repeatable evidence package.
- No high-risk destination ships without policy review.
- Engineering does not maintain a separate enterprise fork.

### Persona 2: Lead AI Agent Engineer Debugging Production-Like Failures

Profile:

```text
Name: Jordan
Company: B2B legal AI platform
Buyer type: Engineering team seat buyer
Main pressure: Debug failed multi-step agent runs without copying customer docs into logs
```

Why Jordan pays:

- Production-like agent runs are hard to reproduce.
- Failures involve model calls, retrieval, tool calls, approvals, and long workflows.
- Raw logs may contain privileged legal documents.
- Teammates need enough context to help without seeing private content.

Workflow:

```text
1. Run the failing workflow in Observe mode.
2. Open Console and inspect the timeline.
3. Identify the span where the model timed out or tool call failed.
4. Export a safe trace with workflow structure, timing, error summary, token counts,
   payload sizes, hashes, and redaction markers.
5. Share safe-trace.json with a teammate.
6. Teammate replays structurally or with mocks.
7. Engineer fixes the agent logic.
8. Run Guard Mode to confirm policy behavior.
9. Commit updated code and policy.
10. CI verifies no undeclared high-risk egress remains.
```

Mock safe debugging flow:

```text
+----------------------+       +----------------------+
| Jordan's machine     |       | Teammate             |
+----------------------+       +----------------------+
| encrypted payloads   |       | safe trace only      |
| safe metadata        | ----> | workflow structure   |
| local reveal only    |       | timing and errors    |
+----------------------+       +----------------------+
```

Success metrics:

- Faster root-cause analysis.
- Fewer private payloads in logs or chat.
- Better regression tests from replay artifacts.
- Safer cross-team debugging.

### Persona 3: Solutions Engineer Preparing A Private Proof Of Concept

Profile:

```text
Name: Priya
Company: AI vendor selling workflow automation to insurance carriers
Buyer type: Revenue team and technical pre-sales user
Main pressure: Demonstrate product value using customer-like data without exposing it
```

Why Priya pays:

- Prospects demand a private proof of concept before purchasing.
- Sales needs customer-facing evidence, not internal engineering logs.
- Support needs safe telemetry during the demo.
- The vendor needs to prove which destinations and data classes are allowed.

Workflow:

```text
1. Ask engineering for the latest signed capsule manifest.
2. Confirm policy declares model providers, CRM tools, and allowed data classes.
3. Run capsule demo create for the prospect.
4. Review customer-verification.html.
5. Share the verification page with the customer security team.
6. Run the private proof of concept.
7. Monitor vendor-telemetry.json for safe health and usage metadata.
8. If the demo fails, share support-bundle.json internally.
9. Fix configuration or policy and regenerate the demo artifacts.
10. Attach final evidence to the sales/security review packet.
```

Mock proof-of-concept evidence packet:

```text
acme-insurance-demo/
  customer-verification.html
  attestation-result.json
  vendor-telemetry.json
  support-bundle.json
  capsule-manifest.json
  policy.json
```

Customer-facing message:

```text
Here is the verification page for the private proof of concept.
It shows the agent version, approved destinations, policy version,
attestation result, and safe telemetry. It does not include your
documents, prompts, tool payloads, outputs, secrets, or identifiers.
```

Success metrics:

- More private proof-of-concepts pass security review.
- Fewer custom documents are needed per prospect.
- Demo failures can be diagnosed without requesting customer data.
- Sales can show concrete evidence rather than generic security claims.

### Persona 4: Enterprise Security Reviewer Evaluating An AI Vendor

Profile:

```text
Name: Elena
Company: Large healthcare enterprise
Buyer type: Enterprise security and governance stakeholder
Main pressure: Approve useful AI agents without losing control of regulated data
```

Why Elena pays or requires it:

- Vendors want to run agents against sensitive workflows.
- Security needs evidence of data movement and policy enforcement.
- Reviewers cannot rely on verbal assurances.
- The enterprise wants support without handing private logs to vendors.

Workflow:

```text
1. Request Agent Capsule evidence from the vendor.
2. Review the signed manifest.
3. Inspect approved model providers and tool destinations.
4. Review policy for high-risk data classes.
5. Confirm secrets are listed by name only.
6. Review customer-verification.html for attestation and runtime evidence.
7. Ask for safe trace examples for failure handling.
8. Confirm CI gates block undeclared high-risk egress.
9. Approve the proof of concept or request policy changes.
10. Store evidence with the enterprise security review record.
```

Security review checklist:

```text
+-------------------------------------------+----------+
| Question                                  | Evidence |
+-------------------------------------------+----------+
| Which version is running?                 | Manifest |
| Which model provider is used?             | Manifest |
| Which tools can the agent call?           | Policy   |
| Which destinations can receive data?      | Policy   |
| What data classes can leave?              | Policy   |
| Are secrets exposed to the vendor?        | Secret   |
|                                           | receipt  |
| Can support debug without plaintext?      | Safe     |
|                                           | trace    |
| Will PRs block unsafe egress?             | CI gate  |
+-------------------------------------------+----------+
```

Success metrics:

- Faster vendor security reviews.
- More precise data-processing approvals.
- Reduced need to share raw logs with vendors.
- Stronger audit trail for AI vendor decisions.

### Persona 5: Enterprise Platform Engineer Operating Customer-Cloud Agents

Profile:

```text
Name: Tomas
Company: Global financial services company
Buyer type: Enterprise platform team
Main pressure: Run external AI agents inside controlled infrastructure with clear evidence
```

Why Tomas pays:

- The enterprise wants AI capabilities inside its own cloud.
- Platform teams need version, policy, secret, and network evidence.
- Rollouts require repeatable deployment checks.
- Support bundles must be sanitized before leaving the environment.

Workflow:

```text
1. Receive signed capsule manifest from the AI vendor.
2. Validate runtime compatibility and policy hash.
3. Provision approved network destinations.
4. Configure customer-controlled secrets or key-management integration.
5. Run attestation verification for the selected confidential environment.
6. Release only required secrets after verification.
7. Monitor safe telemetry: health, timing, token counts, payload sizes, policy decisions.
8. On failure, export a sanitized support bundle.
9. Approve updates only when manifest, policy, and runtime checks pass.
10. Roll back if policy or runtime evidence differs from approval.
```

Customer-cloud workflow:

```text
Vendor signed capsule
    |
    v
Enterprise platform validation
    |
    +--> manifest signature
    +--> policy hash
    +--> runtime version
    +--> destination allowlist
    +--> secret names
    +--> attestation evidence
    |
    v
Secrets released after verification
    |
    v
Agent runs with safe telemetry
    |
    v
Sanitized support bundle if needed
```

Success metrics:

- Clear release approval process.
- Fewer manual deployment exceptions.
- Customer-controlled secrets stay under customer control.
- Vendor support does not require production plaintext logs.
- Updates and rollbacks are evidence-driven.

## 4. Appendix: Commands, Artifacts, And Safety Rules

### 4.1 Core Commands

```bash
# Initialize local Agent Capsule config
python3 -m agent_capsule_cli init

# Run an agent in Observe mode
python3 -m agent_capsule_cli run --mode observe -- <command>

# Run an agent in Guard Mode
python3 -m agent_capsule_cli run --mode guard --policy <policy.json> -- <command>

# List safe traces
python3 -m agent_capsule_cli trace list

# Export a safe trace
python3 -m agent_capsule_cli trace export --safe <run_id> --output safe-trace.json

# Replay a trace structurally
python3 -m agent_capsule_cli trace replay <run_id> --mode structural --output replay.json

# Check privacy policy
python3 -m agent_capsule_cli policy check --policy <policy.json> --trace <trace.json>

# Fail on high-risk egress
python3 -m agent_capsule_cli policy check \
  --policy <policy.json> \
  --trace <trace.json> \
  --fail-on high-risk-egress

# Run CI gate
python3 -m agent_capsule_cli ci check \
  --policy <policy.json> \
  --trace-dir .agent-capsule/traces \
  --manifest .agent-capsule/manifests/capsule-manifest.json \
  --release \
  --annotation-format github \
  --json

# Build signed manifest
python3 -m agent_capsule_cli build \
  --policy <policy.json> \
  --output .agent-capsule/manifests/capsule-manifest.json

# Create confidential-like demo
python3 -m agent_capsule_cli demo create \
  --customer <customer-name> \
  --mode confidential \
  --manifest .agent-capsule/manifests/capsule-manifest.json \
  --policy <policy.json> \
  --trace-dir .agent-capsule/traces \
  --output-dir .agent-capsule/demos
```

### 4.2 UI Commands

Agent Capsule Console:

```bash
cd agent-capsule-console
npm ci
npm run dev -- --port 3018
```

Product website:

```bash
cd agent-capsule-website
npm ci
npm run dev -- --port 3020
```

### 4.3 Repository-Level Verification

```bash
bash ci/check-phase15.sh
```

This runs previous phase checks and verifies the product website.

### 4.4 Policy Decision Order

Agent Capsule evaluates policy in this order:

```text
1. Secrets rule
2. Undeclared high-risk egress rule
3. Undeclared destination rule
4. Destination-specific approval rule
5. Destination-specific redaction rule
6. Destination-specific allowed data rule
7. Allow
```

First matching rule wins.

### 4.5 Supported Policy Actions

```text
+-------------------+---------------------------------------------------------+
| Action            | Meaning                                                 |
+-------------------+---------------------------------------------------------+
| allow             | Payload may proceed unchanged.                          |
| allow_fields      | Only selected fields may proceed.                       |
| redact            | Configured fields or data classes are redacted.         |
| require_approval  | Execution pauses for human approval.                    |
| block             | Call does not execute.                                  |
| warn              | Execution proceeds, warning is recorded.                |
| not_evaluated     | Span does not involve policy-relevant egress.           |
+-------------------+---------------------------------------------------------+
```

### 4.6 Safety Rules To Repeat Internally

```text
Raw prompts stay local by default.
Raw documents stay local by default.
Raw model outputs stay local by default.
Raw tool payloads stay local by default.
Secrets are never printed.
User identifiers are not included in safe traces.
Safe traces are useful for debugging but not plaintext payload archives.
CI findings must be safe to upload as build artifacts.
Hosted confidential demos require real cloud confidential-computing infrastructure.
Local confidential-like demos validate workflow gates but are not hosted confidential hardware.
```

### 4.7 What Good Looks Like

For engineering:

```text
Every agent change that introduces a model, tool, database, or destination
produces safe trace evidence and policy review in the pull request.
```

For security:

```text
Every approved destination, data class, redaction rule, approval requirement,
and blocked path is visible in version-controlled policy.
```

For support:

```text
Every failure can produce a safe trace or sanitized support bundle before
anyone asks for private customer data.
```

For sales:

```text
Every private proof of concept can include a customer verification page,
manifest evidence, policy evidence, attestation result, and safe vendor telemetry.
```

For the founder:

```text
Agent Capsule turns privacy from a launch checklist into an engineering workflow
and turns enterprise trust from a custom promise into repeatable evidence.
```

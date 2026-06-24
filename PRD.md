# Agent Capsule PRD

Product: Private Agent SDK  
Working name: Agent Capsule  
Document status: Draft v0.1  
Date: 2026-06-23  
Primary customer: AI startups building B2B agents  
Initial wedge: Private agent debugging and privacy-safe observability  
Enterprise expansion: Attested customer-cloud deployment, governance, licensing, and metering

## 1. Product Summary

Agent Capsule is a developer-first SDK, CLI, and policy system for building, debugging, and deploying AI agents without exposing sensitive prompts, customer data, credentials, or proprietary agent logic.

The product starts as a local-first privacy debugger. Developers add one SDK to their agent and get encrypted traces, data-flow visibility, privacy-policy checks, safe replay, and sanitized traces they can share with teammates.

Encrypted traces and data-flow visibility must be exposed through a dedicated frontend called Agent Capsule Console. The console should be a separate TypeScript and Next.js codebase that uses shadcn/ui as its component system. It should connect to the local Agent Capsule trace store through a local API bridge, render privacy-safe metadata by default, and require explicit local authorization before revealing any raw encrypted payload content.

When the agent is ready for customer evaluation or deployment, the same SDK and CLI create a signed Agent Capsule that contains:

- Agent package metadata
- Prompt template fingerprints
- Tool definitions
- Model configuration
- Privacy policies
- Network permissions
- Dependency and image hashes
- Secrets requirements
- Usage meters
- Runtime compatibility metadata

The long-term product is the standard way AI startups package, verify, deploy, support, license, and bill private agents running in enterprise-controlled environments.

## 2. Core Product Insight

A pure confidential-computing product is not sticky enough for small developers. Most developers will only think about confidential deployment after an enterprise customer demands it.

Agent Capsule must provide value before that moment.

The entry product is a private-by-default agent debugger that turns real execution behavior into an enterprise-ready privacy and deployment manifest.

Developers use Agent Capsule while:

- Developing the agent
- Debugging model and tool calls
- Testing privacy policies
- Sharing traces with teammates
- Preparing customer demonstrations
- Packaging releases
- Deploying into customer environments
- Supporting production installations

The same SDK remains inside the runtime, which creates natural retention and expansion.

## 3. Problem Statement

### 3.1 Developer Problem

AI agents are difficult to debug because a single run may involve:

- Multiple model calls
- Retrieval systems
- Databases
- External tools
- Internal APIs
- Customer documents
- Credentials
- Long-running workflows
- Human approvals

Existing logs often contain raw prompts, private documents, model outputs, API keys, personally identifiable information, and customer records.

Developers face an uncomfortable choice:

- Upload sensitive traces to an external observability product
- Remove useful trace content and lose debugging capability
- Build custom internal tracing
- Debug manually from incomplete application logs

### 3.2 Startup Problem

When an AI startup sells to larger enterprises, customers ask:

- Where does our data go?
- Which model receives it?
- Which tools can the agent call?
- Does the vendor retain prompts or outputs?
- Can the agent run in our cloud?
- Can the vendor access our environment?
- How do we know which version is running?
- How can the vendor support the agent without seeing our data?

Startups often cannot answer precisely because privacy, deployment, observability, and support are developed separately.

### 3.3 Enterprise Problem

Enterprises want AI capabilities without:

- Sending confidential data into uncontrolled SaaS environments
- Giving vendors permanent administrative access
- Running opaque agent code with unrestricted network access
- Allowing silent model, prompt, or policy changes
- Giving vendors production logs containing sensitive data

They need inspectable policies and verifiable deployment evidence.

### 3.4 Product Gap

Generic bring-your-own-cloud and self-hosted distribution platforms help vendors install and manage software in customer cloud accounts. Agent Capsule should not rebuild those categories.

Agent Capsule differentiates through agent-specific privacy inspection, policy generation, safe traces, attested packaging, confidential runtime verification, and language-native developer ergonomics.

## 4. Product Vision

Near-term vision:

> Make Agent Capsule the tool developers open whenever they need to answer: What did my agent do, what data did it expose, and how can I safely reproduce the run?

Long-term vision:

> Make Agent Capsule the artifact enterprises request from every external AI vendor: Send us your Agent Capsule so we can inspect its policies, verify its software, and run it privately.

Positioning:

- For developers: Private debugging and deployment for AI agents.
- For AI startups: Turn your agent into an enterprise-ready private product without maintaining a separate enterprise codebase.
- For enterprises: Run external AI agents in your environment with inspectable permissions and verifiable software identity.

## 5. Product Principles

### 5.1 Local-First Privacy

Raw prompts, documents, tool payloads, model responses, and secrets remain on the developer's machine by default.

The Agent Capsule control plane may receive operational metadata, but not raw trace content unless the user explicitly enables encrypted synchronization.

### 5.2 Useful Before Enterprise Adoption

The free product must solve a daily developer problem independently of confidential computing or enterprise sales.

Developers should install Agent Capsule because it makes debugging easier.

### 5.3 Progressive Security

Agent Capsule supports three operating modes:

- Observe mode: Captures agent behavior and identifies data movement without blocking execution.
- Guard mode: Applies policies to model calls, tool calls, and supported network traffic. It can warn, redact, require approval, or block.
- Confidential mode: Runs the packaged agent inside an attested confidential environment and releases protected assets only after verification.

### 5.4 One Codebase

Developers should not rewrite the agent to move from:

- Local development
- Team testing
- Hosted private demonstration
- Customer VPC
- Enterprise production

### 5.5 Verifiable Rather Than Trusted

The product should produce evidence that can be independently checked:

- Container digest
- Agent manifest signature
- Policy version
- Model identifier or model artifact hash
- Attestation result
- Approved network destinations
- Release history

### 5.6 Language-Native, Spec-Consistent

Agent Capsule must feel natural in each supported language while producing the same trace schema, policy behavior, manifest format, and CI results across languages.

Supported SDK targets:

- Python
- TypeScript and JavaScript
- Java
- Go
- Rust

Python is the recommended MVP wedge. The shared capsule specification must be designed from the start so the other SDKs can reach parity without changing policy files or trace formats.

## 6. Target Users

### 6.1 Primary User: AI Agent Developer

Profile:

- Builds document, workflow, research, financial, legal, healthcare, or support agents
- Uses model APIs, retrieval systems, and external tools
- Frequently debugs multi-step behavior
- May handle sensitive customer data
- Works in Python, TypeScript, Java, Go, or Rust depending on company stack

Primary jobs:

- Understand why an agent failed
- See which model and tools were called
- Inspect data passed between components
- Replay a failed run safely
- Share a trace without exposing private content
- Test whether an agent violates privacy policies
- Package the agent for a customer demonstration

### 6.2 Primary Buyer: Founder or CTO

Primary jobs:

- Avoid building a separate enterprise edition
- Respond to security questionnaires
- Close customer-cloud or private-deployment deals
- Protect proprietary prompts, code, and model assets
- Reduce engineering time spent on custom deployments
- Create a repeatable enterprise deployment process

### 6.3 Secondary User: Solutions Engineer

Primary jobs:

- Prepare a private proof of concept
- Configure customer-specific integrations
- Validate network and tool access
- Generate a privacy report
- Diagnose deployment issues without accessing customer data

### 6.4 Future Enterprise User: Security Reviewer

Primary jobs:

- Inspect what the agent can access
- Approve network and tool permissions
- Verify the deployed version
- Review attestation results
- Approve updates
- Export evidence to internal security systems

### 6.5 Future Enterprise User: Platform Engineer

Primary jobs:

- Install the agent in the enterprise cloud
- Connect customer-controlled secrets
- Configure private networking
- Monitor health
- Apply update and rollback policies
- Produce sanitized support bundles

## 7. Jobs To Be Done

Developer JTBD:

- When an agent produces an unexpected result, I want to inspect and replay the entire workflow without uploading sensitive inputs to an external service.

Privacy JTBD:

- When my agent gains access to a new model, tool, database, or network destination, I want to know exactly which data could leave the process and block anything undeclared.

Deployment JTBD:

- When a customer asks for private deployment, I want to package the same agent I already run locally rather than creating a separate enterprise version.

Sales JTBD:

- When a customer's security team asks how the agent handles data, I want to generate an accurate report from actual runtime behavior rather than manually completing a spreadsheet.

Support JTBD:

- When a customer-hosted agent fails, I want enough diagnostic information to fix it without seeing the customer's prompts, documents, or outputs.

Billing JTBD:

- When an agent runs inside a customer-controlled environment, I want a trustworthy usage summary without collecting customer content.

## 8. Product Scope

### 8.1 Phase 1: Sticky Developer Product

The first product is a local-first SDK, CLI, and debugging interface.

It includes:

- Agent execution tracing
- Local encrypted trace storage
- Model-call and tool-call timelines
- Agent Capsule Console as a separate TypeScript and Next.js frontend
- shadcn/ui-based interface for trace exploration and data-flow visibility
- Privacy and egress map
- Sensitive-data annotations
- Safe trace sharing
- Run comparison
- Replay
- Policy linting
- Signed Agent Capsule manifest
- Docker packaging
- Confidential demonstration environment
- Python SDK
- Shared schema, CLI, and policy engine designed for multi-language SDKs
- Product website requirements for a separate Next.js and shadcn/ui marketing codebase

### 8.2 Phase 1.5: Multi-Language and Team Features

Phase 1.5 extends the product beyond the Python wedge:

- TypeScript SDK
- Java SDK
- Go SDK
- Rust SDK
- Encrypted team trace synchronization
- Team roles
- Shared policies
- Release registry
- Usage meters
- Signed usage summaries
- Hosted confidential environments
- Longer trace retention
- CI/CD integrations

### 8.3 Phase 2: Enterprise Product

Phase 2 includes:

- Customer-cloud installation
- Customer-controlled keys
- Attestation-based secret release
- Enterprise policy approval
- Egress enforcement
- Release approvals
- SSO and RBAC
- SIEM integration
- Audit evidence
- Signed billing receipts
- Update and rollback controls
- Cross-language runtime certification

### 8.4 Explicit Non-Goals For MVP

Agent Capsule will not initially:

- Build or train foundation models
- Operate a general-purpose GPU cloud
- Replace LangChain, LlamaIndex, OpenAI Agents SDK, Spring AI, Semantic Kernel, or other agent frameworks
- Guarantee that an agent is logically safe
- Eliminate prompt injection
- Prevent all forms of model extraction
- Provide full regulatory compliance certification
- Support air-gapped installations
- Support every cloud provider
- Provide a public agent marketplace
- Inspect arbitrary operating-system traffic outside supported instrumentation
- Guarantee privacy when data is intentionally sent to an external model provider

## 9. Supported Languages And SDK Requirements

### 9.1 Language Support Strategy

Agent Capsule must support multiple languages without creating different product behavior per language.

Each SDK must implement:

- Shared trace event schema
- Shared policy evaluation semantics
- Shared redaction and hashing semantics
- Shared safe trace export format
- Shared capsule manifest format
- Shared CLI compatibility
- Language-native instrumentation hooks
- Language-native error types
- OpenTelemetry bridge where practical

The CLI should be installable independently and able to validate artifacts from every language.

### 9.2 Language Targets

| Language | Package | MVP priority | Runtime baseline | Primary use cases |
| --- | --- | --- | --- | --- |
| Python | `agent-capsule` | P0 | Python 3.10+ | Agent startups, notebooks, LangChain/LlamaIndex/OpenAI SDK integrations |
| TypeScript | `@agent-capsule/sdk` | P1 | Node.js 20+ | Node agents, web service agents, Vercel/Next.js backends |
| Java | `com.agentcapsule:sdk` | P1 | Java 17+ | Enterprise agents, Spring AI, JVM services |
| Go | `github.com/agentcapsule/agent-capsule-go` | P1 | Go 1.22+ | Backend services, infra-heavy agents, high-throughput tool calls |
| Rust | `agent-capsule` crate | P1 | Rust stable | safety-sensitive services, high-performance runtimes, edge systems |

### 9.3 Cross-Language API Shape

Each SDK should expose the same conceptual primitives:

- `Capsule`
- `Trace`
- `Span`
- `Policy`
- `Destination`
- `DataClass`
- `ToolCall`
- `ModelCall`
- `SafeTrace`
- `ApprovalRequest`

Each SDK should support:

- Initialize capsule runtime
- Start and finish runs
- Wrap model clients
- Wrap tool calls
- Annotate sensitive fields
- Register destinations
- Evaluate policies
- Export safe traces
- Build capsule metadata

### 9.4 Example SDK Usage

Python:

```python
from agent_capsule import Capsule

capsule = Capsule.init(mode="observe", policy="agent-capsule.policy.yaml")

with capsule.run("claim-triage") as run:
    result = agent.invoke(input_claim)
    run.record_output(result)
```

TypeScript:

```ts
import { Capsule } from "@agent-capsule/sdk";

const capsule = await Capsule.init({
  mode: "observe",
  policy: "agent-capsule.policy.yaml",
});

await capsule.run("claim-triage", async (run) => {
  const result = await agent.invoke(inputClaim);
  run.recordOutput(result);
});
```

Java:

```java
Capsule capsule = Capsule.init(
    CapsuleConfig.builder()
        .mode(CapsuleMode.OBSERVE)
        .policyPath("agent-capsule.policy.yaml")
        .build()
);

capsule.run("claim-triage", run -> {
    AgentResult result = agent.invoke(inputClaim);
    run.recordOutput(result);
});
```

Go:

```go
capsule, err := agentcapsule.Init(agentcapsule.Config{
    Mode:       agentcapsule.Observe,
    PolicyPath: "agent-capsule.policy.yaml",
})
if err != nil {
    return err
}

err = capsule.Run(ctx, "claim-triage", func(run *agentcapsule.Run) error {
    result, err := agent.Invoke(ctx, inputClaim)
    if err != nil {
        return err
    }
    run.RecordOutput(result)
    return nil
})
```

Rust:

```rust
use agent_capsule::{Capsule, CapsuleConfig, Mode};

let capsule = Capsule::init(CapsuleConfig {
    mode: Mode::Observe,
    policy_path: "agent-capsule.policy.yaml".into(),
})?;

capsule.run("claim-triage", |run| async move {
    let result = agent.invoke(input_claim).await?;
    run.record_output(&result)?;
    Ok(())
}).await?;
```

### 9.5 Language-Specific Instrumentation Requirements

Python:

- Decorators and context managers for runs, tools, and model calls
- Wrappers for common model SDKs
- Optional integrations for LangChain, LlamaIndex, OpenAI Agents SDK, and direct OpenAI SDK usage
- Pydantic-based structured payload annotations

TypeScript:

- Async context propagation
- Middleware wrappers for model clients and tools
- Framework hooks for Node service runtimes
- Zod-based structured payload annotations

Java:

- Builder-style configuration
- Spring Boot auto-configuration
- Interceptors for HTTP clients and model clients
- Annotation-based field classification

Go:

- Context-based propagation
- Explicit wrapper functions
- Struct tags for field classification
- HTTP middleware for supported clients

Rust:

- `tracing` integration
- Attribute macros where useful
- Serde-based field classification
- Async runtime compatibility for Tokio

## 10. Core Use Case

Scenario: a startup builds an insurance claims-triage agent.

The agent:

- Reads claim documents
- Extracts policy and incident details
- Queries an internal policy database
- Calls an OCR service
- Uses a language model
- Produces a recommended classification
- Escalates certain claims to a human reviewer

Current workflow:

- Engineers send traces to a hosted observability platform.
- Traces may contain claimant names, addresses, policy numbers, medical details, accident descriptions, model responses, and internal tool output.
- The startup later tries to sell to an insurer.
- The insurer refuses to send production claims to the startup's SaaS platform.
- The startup now needs custom deployment, logging, networking, secrets, update, and support systems.

Workflow with Agent Capsule:

1. The developer installs the SDK.
2. Agent Capsule captures model and tool calls locally.
3. Raw claims remain in an encrypted local trace store.
4. The privacy map shows every destination receiving claim information.
5. The developer marks medical information as restricted.
6. A policy prevents medical details from being sent to the external OCR service.
7. The developer replays the workflow using the corrected policy.
8. Agent Capsule generates a sanitized trace for team review.
9. The developer runs `capsule build`.
10. The system creates a signed image and Agent Capsule manifest.
11. The agent is deployed into a confidential demonstration environment.
12. The insurer receives a verification page showing release identity, declared tools, destinations, and privacy policy.
13. In the enterprise phase, the same capsule is installed in the insurer's cloud.
14. The startup receives health metadata and signed claim-count totals, but no raw claim content.

Result:

- The developer receives a better debugging tool immediately.
- The startup gains a repeatable enterprise deployment path.
- The insurer gains visibility and control without needing access to the startup's proprietary code or prompts.

## 11. User Journeys

### 11.1 Journey A: First Developer Experience

Trigger: A developer wants to debug an existing Python agent.

Steps:

1. Developer installs the package with `pip install agent-capsule`.
2. Developer runs `capsule init`.
3. The CLI creates `agent-capsule.policy.yaml`, `.agent-capsule/`, and local encryption settings.
4. Developer wraps the agent entrypoint with the SDK.
5. Developer runs the agent in Observe mode.
6. Agent Capsule records a local encrypted trace.
7. Developer opens Agent Capsule Console with `capsule view`.
8. The CLI starts a localhost-only API bridge with an ephemeral session token.
9. The TypeScript and Next.js console renders encrypted trace metadata, model calls, tool calls, approvals, errors, token counts, payload sizes, and data-flow visibility.
10. Developer selects a failed run and inspects the workflow graph without exposing raw payloads by default.
11. Developer exports a safe trace for a teammate.

Success condition:

- Developer can understand an agent run without uploading raw prompts, documents, outputs, or secrets to a third-party observability service.

### 11.2 Journey B: Safe Replay

Trigger: A developer needs to reproduce a failed run without exposing private content.

Steps:

1. Developer selects a failed local trace.
2. Agent Capsule identifies payloads that cannot be replayed in plaintext.
3. Developer chooses a replay profile:
   - Structural replay
   - Mocked tool replay
   - Redacted payload replay
   - Approved plaintext replay on local machine
4. The system rebuilds the run graph.
5. The system substitutes redacted values, hashes, mocks, or developer-approved local values.
6. Developer reruns the workflow.
7. The replay output is compared to the original trace.
8. Differences are shown by span, component, timing, token count, and policy decision.

Success condition:

- Developer can reproduce and debug workflow behavior without sending sensitive source payloads outside the approved environment.

### 11.3 Journey C: Privacy Review

Trigger: The team adds a new CRM tool.

Steps:

1. Developer runs the agent in Observe mode.
2. The privacy map detects the new destination.
3. The system shows that email addresses and account notes are being sent to the CRM.
4. The destination is not declared in the policy.
5. Agent Capsule generates a warning.
6. Developer chooses one action:
   - Allow the destination
   - Allow only selected data fields
   - Redact specified fields
   - Require human approval
   - Block the tool
7. The policy is stored in version control.
8. CI runs `capsule policy check`.
9. The pull request cannot merge if undeclared high-risk egress remains.

Success condition:

- Privacy behavior becomes part of the engineering workflow rather than a separate review before launch.

### 11.4 Journey D: Safe Team Collaboration

Trigger: A developer needs help diagnosing a failed production-like run.

Steps:

1. Developer chooses `Create safe trace`.
2. Agent Capsule removes or hashes:
   - Prompt content
   - Document text
   - Model outputs
   - Tool payloads
   - Secrets
   - User identifiers
3. The safe trace retains:
   - Workflow structure
   - Timing
   - Component versions
   - Error messages
   - Token counts
   - Payload sizes
   - Policy decisions
   - Content hashes
   - Redaction markers
4. Developer shares the trace with a teammate.
5. The teammate can inspect the failure without viewing private data.

Success condition:

- The trace is sufficiently useful for diagnosis while containing no plaintext sensitive payloads.

### 11.5 Journey E: Confidential Customer Demonstration

Trigger: A prospective enterprise customer asks for a private proof of concept.

Steps:

1. Developer runs `capsule demo create --customer acme-insurance --mode confidential`.
2. The CLI checks that the agent has a current policy file, signed manifest, reproducible build metadata, and declared network destinations.
3. The CLI builds a container image or records the digest of an existing image.
4. Agent Capsule creates a signed capsule manifest containing:
   - Agent name and version
   - Language runtime and SDK version
   - Container digest
   - Dependency lockfile hashes
   - Prompt template hashes
   - Tool definitions
   - Model configuration
   - Policy version
   - Required secrets
   - Declared network destinations
   - Usage meter definitions
5. The confidential demo environment starts from the signed manifest.
6. Secrets are released only after the environment passes verification.
7. The customer receives a verification page showing:
   - Capsule identity
   - Attestation status
   - Approved model providers
   - Approved tools
   - Approved network destinations
   - Policy version
   - Data classes that may leave the environment
8. The customer runs private evaluation data through the demo.
9. The vendor can view health, timing, error class, token count, payload size, policy decision, and usage metadata.
10. The vendor cannot view customer prompts, documents, tool payloads, model outputs, secrets, or user identifiers.

Success condition:

- The startup can run a credible private proof of concept without building a separate enterprise edition and without receiving the customer's plaintext data.

## 12. Functional Requirements

### 12.1 SDK Initialization

The SDK must:

- Initialize in Observe, Guard, or Confidential mode
- Load policy from a local path, environment variable, or packaged capsule manifest
- Create a run context
- Propagate context across async, thread, worker, or coroutine boundaries where supported
- Record language, runtime, SDK version, framework integrations, and component versions
- Fail closed in Guard and Confidential modes when policy cannot be loaded
- Fail open with warnings in Observe mode when policy cannot be loaded

### 12.2 Trace Capture

The SDK must capture:

- Run ID
- Span ID and parent span ID
- Start and end time
- Component name and type
- Language runtime
- Model calls
- Tool calls
- Retrieval calls
- Database calls where instrumented
- Network destinations where instrumented
- Token counts
- Payload sizes
- Error messages and stack summaries
- Policy decisions
- Redaction markers
- Content hashes

Trace capture must not require raw payloads to leave the local machine.

### 12.3 Local Encrypted Trace Store

The trace store must:

- Encrypt raw trace payloads at rest
- Store metadata separately from raw payload content
- Support configurable retention
- Support deletion by run ID
- Support safe trace export
- Support policy migration across stored traces
- Provide a local-only mode with no cloud sync

### 12.4 Privacy Map

The privacy map must show:

- Data classes detected in each run
- Source components
- Destination components
- Model providers
- Tool providers
- External domains
- Internal service destinations
- Policy status for each destination
- Risk level
- Action taken

The privacy map must detect when new destinations appear in observed runs.

### 12.5 Policy Engine

The policy engine must support:

- Declared destinations
- Declared tools
- Declared model providers
- Data class rules
- Field-level allowlists
- Field-level redaction
- Human approval requirements
- Blocking rules
- Risk classification
- CI policy checks
- Policy versioning
- Signed policy artifacts

Policy actions:

- `allow`
- `allow_fields`
- `redact`
- `require_approval`
- `block`
- `warn`

Example policy:

```yaml
version: 1
agent:
  name: claims-triage
  owner: platform-team

destinations:
  crm:
    type: external_tool
    domain: api.crm.example
    risk: high
    allowed_data:
      - account_id
      - support_tier
    redact:
      - email
      - account_notes
    require_approval:
      - medical_information

defaults:
  undeclared_high_risk_egress: block
  undeclared_destination: warn
  secrets: block
```

### 12.6 Guard Mode Enforcement

Guard mode must:

- Evaluate policy before supported model calls, tool calls, and network egress
- Redact configured fields before payload leaves the process
- Request human approval when policy requires it
- Block calls that violate policy
- Record every decision in the trace
- Provide deterministic CI behavior for policy checks

### 12.7 Safe Trace Export

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

### 12.8 Replay

Replay must support:

- Replaying run structure
- Replaying with mocked model responses
- Replaying with mocked tool results
- Replaying with approved local plaintext payloads
- Comparing original and replayed traces
- Highlighting changed policy decisions
- Highlighting changed destinations

### 12.9 Capsule Build

`capsule build` must:

- Validate policy
- Validate manifest metadata
- Capture language runtime metadata
- Capture package manager metadata
- Capture dependency lockfile hashes
- Capture container image digest when available
- Capture prompt template hashes without storing prompt plaintext
- Capture tool schemas
- Capture model configuration
- Sign the manifest
- Emit a build report

### 12.10 Confidential Demo

`capsule demo create` must:

- Require a valid signed manifest
- Require a policy with no undeclared high-risk egress
- Start a confidential or confidential-like hosted environment
- Verify the runtime before releasing secrets
- Generate a customer verification page
- Restrict vendor observability to safe metadata
- Produce a sanitized support bundle when the demo fails

### 12.11 Agent Capsule Console

Agent Capsule Console is the dedicated UI for encrypted traces and data-flow visibility.

The console must be built as a separate frontend codebase:

- Codebase name: `agent-capsule-console`
- Framework: Next.js with App Router
- Language: TypeScript
- UI system: shadcn/ui
- Styling: Tailwind CSS
- Package manager: pnpm preferred, npm supported
- Runtime: Node.js 20+

The console must remain local-first:

- It must connect to local trace data through a localhost-only API bridge started by `capsule view`.
- It must receive an ephemeral session token from the CLI.
- It must display safe metadata by default.
- It must not send raw prompts, documents, model outputs, tool payloads, secrets, or user identifiers to any remote service by default.
- It must require explicit local authorization before requesting plaintext payload reveal from the encrypted trace store.
- It must record any plaintext reveal action in the local audit trail.

The console must include these primary views:

- Runs dashboard
- Trace timeline
- Span detail drawer
- Data-flow graph
- Privacy map
- Destination review queue
- Policy decision viewer
- Safe trace export flow
- Replay comparison view
- Manifest inspector
- Local settings page

The console must support these user actions:

- Search runs by ID, status, component, destination, data class, risk, and policy decision
- Filter traces by model call, tool call, retrieval call, database call, network destination, approval, and error
- Inspect encrypted trace metadata without exposing raw payloads
- Reveal raw local payloads only through an explicit local-only confirmation
- Generate policy suggestions from observed destinations
- Copy policy diffs into `agent-capsule.policy.yaml`
- Export safe traces
- Start replay from a selected run
- Compare original and replayed runs
- Inspect signed capsule manifests

### 12.12 Agent Capsule Console API Bridge

The CLI must expose a local API bridge for the console.

The bridge must:

- Bind to `127.0.0.1` by default
- Use an ephemeral port unless the developer passes `--port`
- Require an ephemeral session token
- Read from the encrypted local trace store
- Return safe metadata by default
- Keep payload reveal endpoints disabled unless the user explicitly enables local reveal
- Shut down when the console session ends unless `--keep-alive` is set

Required local API endpoints:

- `GET /health`
- `GET /runs`
- `GET /runs/:run_id`
- `GET /runs/:run_id/timeline`
- `GET /runs/:run_id/data-flow`
- `GET /runs/:run_id/privacy-map`
- `GET /runs/:run_id/policy-decisions`
- `POST /runs/:run_id/export-safe-trace`
- `POST /runs/:run_id/replay`
- `GET /manifests/:manifest_id`
- `POST /payloads/:payload_id/reveal-local`

The `reveal-local` endpoint must:

- Require explicit confirmation from the local user
- Return only the requested payload
- Avoid writing plaintext payloads to console logs
- Emit a local audit event
- Be unavailable in shared, hosted, CI, and customer-demo views

### 12.13 Hardware And Runtime Requirements

Agent Capsule should not require specialized local hardware for the MVP developer workflow.

No specialized hardware is required for:

- SDK instrumentation
- Observe mode
- Guard mode policy evaluation
- Local encrypted trace storage
- Agent Capsule Console
- Safe trace export
- Replay with mocked or redacted payloads
- `capsule policy check`
- `capsule ci check`

Recommended local developer environment:

- CPU: modern 2-core processor minimum, 4-core processor recommended
- Memory: 8 GB RAM minimum, 16 GB RAM recommended for large traces or local agent workloads
- Disk: 1 GB free for SDK, CLI, and console; additional disk depends on trace retention and payload size
- Operating systems: macOS, Linux, and Windows through WSL for MVP; native Windows support should be validated before enterprise GA
- Network: internet access for external model providers, tool calls, package installation, and optional encrypted team sync
- GPU: not required unless the developer's own agent runs local models
- TPM, Secure Enclave, or local HSM: not required for local development

Required software runtimes:

- Python 3.10+ for the Python SDK
- Node.js 20+ for Agent Capsule Console and TypeScript tooling
- Docker for `capsule build` and container-based local release validation
- Git for version-controlled policies and CI workflows

Confidential mode requirements:

- Confidential mode does not require a special developer machine.
- Hosted confidential demonstrations require a supported cloud confidential-computing environment.
- Customer-cloud deployments require the customer's cloud account to support the selected confidential VM, container, enclave, or trusted execution environment.
- Attestation requires access to the chosen platform's attestation service.
- Secret release requires an integrated secrets provider or key-management service.

Production sizing guidance:

- Agent Capsule overhead should be small relative to model latency and external tool latency.
- CPU and memory requirements scale with trace volume, payload metadata size, retention settings, and replay workload.
- High-throughput production deployments should size trace buffering, export workers, and encrypted storage independently from the agent's model-serving capacity.
- If the agent runs local models, retrieval indexes, OCR, or other compute-heavy tools, those components define the hardware requirement, not Agent Capsule itself.

## 13. CLI Requirements

The CLI must support:

```bash
capsule init
capsule run --mode observe -- <command>
capsule view
capsule trace list
capsule trace export --safe <run-id>
capsule trace replay <run-id>
capsule policy check
capsule policy update
capsule build
capsule demo create
capsule manifest inspect
capsule ci check
```

CLI behavior:

- Must work with artifacts produced by any supported language SDK
- `capsule view` must start the local API bridge and open Agent Capsule Console
- `capsule view --no-open` must start the local API bridge without opening a browser
- `capsule view --console-url <url>` must allow development against a separately running Next.js console
- Must print clear warnings for undeclared destinations
- Must return non-zero exit codes for failed CI checks
- Must produce machine-readable JSON output with `--json`
- Must avoid printing raw sensitive payloads unless explicitly requested with local-only confirmation

## 14. CI/CD Requirements

CI must support:

- GitHub Actions
- GitLab CI
- Buildkite
- Generic shell usage

`capsule policy check` must fail when:

- Undeclared high-risk egress remains
- A destination appears in traces but not policy
- A high-risk data class is sent to an unapproved destination
- Policy file is malformed
- Policy version is older than the required minimum
- Manifest signature is missing for release builds
- Runtime language version is unsupported for release builds

Example GitHub Action:

```yaml
name: Agent Capsule

on:
  pull_request:

jobs:
  capsule-policy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: agent-capsule/setup-capsule@v1
      - run: capsule policy check --fail-on high-risk-egress
```

## 15. Data Model

### 15.1 Trace Event

Required fields:

- `trace_id`
- `run_id`
- `span_id`
- `parent_span_id`
- `timestamp_start`
- `timestamp_end`
- `component_type`
- `component_name`
- `language`
- `runtime_version`
- `sdk_version`
- `payload_size_bytes`
- `content_hash`
- `data_classes`
- `destination`
- `policy_decision`
- `error_summary`

### 15.2 Destination

Required fields:

- `id`
- `type`
- `domain`
- `provider`
- `environment`
- `risk`
- `declared_in_policy`
- `allowed_data_classes`
- `observed_data_classes`

### 15.3 Safe Trace

Required fields:

- `safe_trace_version`
- `source_trace_id`
- `created_at`
- `created_by`
- `redaction_profile`
- `workflow_graph`
- `spans`
- `component_versions`
- `policy_decisions`
- `content_hashes`
- `redaction_markers`
- `diagnostic_summary`

### 15.4 Capsule Manifest

Required fields:

- `manifest_version`
- `agent_name`
- `agent_version`
- `language`
- `runtime_version`
- `sdk_version`
- `container_digest`
- `dependency_hashes`
- `prompt_template_hashes`
- `tool_definitions`
- `model_configuration`
- `policy_hash`
- `policy_version`
- `network_destinations`
- `required_secrets`
- `usage_meters`
- `signature`

## 16. Security And Privacy Requirements

Agent Capsule must:

- Keep raw payloads local by default
- Encrypt local raw traces at rest
- Avoid sending plaintext prompts, documents, outputs, tool payloads, secrets, and user identifiers to the control plane by default
- Provide deterministic redaction and hashing
- Detect common secret formats
- Allow custom data classifiers
- Provide field-level data classification
- Record policy decisions without storing the blocked payload in plaintext
- Support customer-controlled keys in enterprise environments
- Release secrets only after environment verification in Confidential mode

Security-sensitive defaults:

- Undeclared high-risk egress blocks release builds
- Secrets are always blocked unless a destination is explicitly marked as a secrets provider
- Safe trace export never includes raw payloads by default
- CI output never prints raw payloads

## 17. User Experience Requirements

Agent Capsule Console must feel like a developer observability tool, not a marketing site. It should prioritize fast scanning, dense but readable trace information, and clear privacy decisions.

The console must show:

- Run timeline
- Model calls
- Tool calls
- Errors
- Token counts
- Payload sizes
- Encrypted trace status
- Trace retention state
- Privacy map
- Data-flow graph
- New destination warnings
- Policy decisions
- Safe trace export action
- Replay action
- Manifest inspection

The UI must support:

- Filtering by run, component, destination, data class, risk, and policy decision
- Inspecting safe metadata without exposing raw payloads by default
- Explicit local-only reveal for raw payloads
- Copying CI-ready policy suggestions
- Exporting a safe trace

Recommended shadcn/ui components:

- `Sidebar` for primary navigation
- `Table` for run and span lists
- `Card` for compact metric summaries
- `Tabs` for timeline, data flow, privacy, replay, and manifest views
- `Sheet` or `Drawer` for span detail inspection
- `Dialog` for local-only plaintext reveal confirmation
- `Badge` for risk, policy decision, and data class labels
- `Tooltip` for technical metadata
- `Select`, `Checkbox`, and `Input` for filters
- `Resizable` for split trace and graph panes
- `Scroll Area` for long span details
- `Sonner` for status notifications

Core screen requirements:

- Runs dashboard: list recent runs, status, duration, token count, error count, destination count, and highest risk.
- Trace detail: show chronological spans, nested workflow structure, timing, component versions, and errors.
- Data-flow graph: show sources, transformations, tools, model providers, databases, and external destinations.
- Privacy map: show observed data classes, declared policy status, risk, and available policy actions.
- Destination review: show undeclared destinations and allow developers to choose allow, allow selected fields, redact, require approval, or block.
- Safe trace export: preview what will be removed, hashed, and retained before export.
- Replay comparison: compare original and replayed runs by span, timing, token count, destination, and policy decision.
- Manifest inspector: show signed capsule identity, language runtime, dependency hashes, model configuration, network destinations, and policy version.

Design constraints:

- Raw payloads must never be visible on first render.
- Reveal controls must be explicit, local-only, and visually distinct from metadata inspection.
- High-risk egress must be visible without requiring users to click into every span.
- Empty states must guide the developer toward `capsule run --mode observe -- <command>`.
- CI-blocking issues must be copyable as policy diffs or command-line remediation steps.

## 18. UI Documentation And Runbook

The repository must include documentation for Agent Capsule Console in `agent-capsule-console/README.md` and product-facing UI documentation in the main PRD or docs site.

### 18.1 Codebase Layout

Recommended separate frontend layout:

```text
agent-capsule-console/
  app/
    page.tsx
    runs/
    traces/
    privacy/
    replay/
    manifests/
    settings/
  components/
    console/
    graph/
    privacy/
    trace/
    ui/
  lib/
    api/
    auth/
    formatting/
    policy/
    trace/
  public/
  README.md
  components.json
  package.json
  tailwind.config.ts
  tsconfig.json
```

### 18.2 Creating The Frontend Codebase

Use the official shadcn/ui Next.js setup flow for a new TypeScript Next.js app:

```bash
pnpm dlx shadcn@latest init -t next
```

For an existing Next.js project:

```bash
pnpm dlx shadcn@latest init
```

Add the first UI components:

```bash
pnpm dlx shadcn@latest add button card badge table tabs dialog sheet dropdown-menu select input checkbox tooltip separator scroll-area sonner resizable
```

### 18.3 Running The Console Locally

Install dependencies:

```bash
cd agent-capsule-console
pnpm install
```

Start the Agent Capsule local API bridge:

```bash
capsule view --no-open --port 4318
```

In a second terminal, point the console at the local bridge and start the Next.js development server:

```bash
NEXT_PUBLIC_CAPSULE_API_URL=http://127.0.0.1:4318 pnpm dev
```

For the normal user flow, the developer should not need to run the frontend manually. They should run:

```bash
capsule view
```

`capsule view` should start the local API bridge, pass an ephemeral session token to the console, and open the browser automatically.

### 18.4 Using The Console

Developer workflow:

1. Run an instrumented agent in Observe mode.
2. Open Agent Capsule Console with `capsule view`.
3. Select a run from the dashboard.
4. Inspect the timeline and data-flow graph.
5. Review undeclared destinations in the privacy map.
6. Choose a policy action for each warning.
7. Export a safe trace or start replay if diagnosis requires it.
8. Copy policy suggestions into `agent-capsule.policy.yaml`.
9. Run `capsule policy check` before opening a pull request.

### 18.5 UI Documentation Requirements

The console documentation must include:

- Overview of each screen
- How encrypted traces are represented
- How data-flow graph nodes and edges are defined
- What metadata is safe to share
- What actions can reveal plaintext locally
- How safe trace export works
- How policy suggestions are generated
- How to configure the local API URL
- How to run the console in development
- How to build the console for production
- How to test the UI
- How to add shadcn/ui components
- How to keep UI terminology aligned with CLI and SDK terminology

### 18.6 Production Build

Build the frontend:

```bash
pnpm build
```

Run the production server:

```bash
pnpm start
```

The release build should be packaged so `capsule view` can serve the compiled console locally without requiring the developer to install frontend dependencies.

## 19. Product Website Requirements

Agent Capsule needs a product website that is separate from the Agent Capsule Console and separate from the SDK/CLI codebase. This PRD documents the required website codebase and design direction. The website implementation should be created only when the team explicitly starts website implementation work.

### 19.1 Website Purpose

The product website must explain Agent Capsule to AI startup founders, CTOs, agent developers, solutions engineers, and enterprise security reviewers.

The website should communicate:

- Private debugging for AI agents
- Encrypted local traces
- Data-flow visibility
- Policy-driven privacy review
- Safe trace sharing
- CI-based egress checks
- Confidential customer demonstrations
- Multi-language SDK support
- No specialized local hardware requirement for the developer workflow

The website should not be a documentation portal, a console UI, or a generic landing page disconnected from the product. It should be a product website that makes the enterprise value clear in the first viewport.

### 19.2 Website Codebase Requirements

The product website must be a separate codebase.

Recommended codebase:

```text
agent-capsule-website/
  app/
  components/
    marketing/
    sections/
    ui/
  lib/
  public/
  README.md
  components.json
  package.json
  tailwind.config.ts
  tsconfig.json
```

Technical requirements:

- Framework: Next.js with App Router
- Language: TypeScript
- UI system: shadcn/ui from `https://ui.shadcn.com`
- Styling: Tailwind CSS
- Runtime: Node.js 20+
- Package manager: pnpm preferred, npm supported
- Copy language: US English
- Deployment target: static or server-rendered Next.js hosting

The website codebase must remain separate from:

- Python SDK
- TypeScript SDK
- Java SDK
- Go SDK
- Rust SDK
- CLI
- Agent Capsule Console

### 19.3 shadcn/ui Setup Requirements

For a new Next.js website:

```bash
pnpm dlx shadcn@latest init -t next
```

For an existing Next.js website:

```bash
pnpm dlx shadcn@latest init
```

If npm is used instead of pnpm:

```bash
npx shadcn@latest init
```

Recommended starting components:

```bash
pnpm dlx shadcn@latest add button card badge table separator tabs accordion
```

The implementation must override any generated component defaults that conflict with the visual rules in this PRD, especially bold font weights and icon affordances.

### 19.4 Website Design Direction

The website must have an enterprise look:

- Restrained layout
- High information clarity
- Dense but readable sections
- Quiet color palette with neutral surfaces and limited accent color
- Clear evidence blocks instead of hype-heavy claims
- Product workflow visuals instead of abstract decoration
- Predictable navigation
- No oversized playful styling
- No emojis
- No icons
- No decorative icon systems
- No icon libraries in the visible UI
- No bold fonts

Font-weight requirements:

- Use normal font weight for body text, headings, navigation, cards, and buttons.
- Avoid `font-bold`, `font-semibold`, and similar bold utility classes.
- If shadcn/ui components include medium or bold defaults, override them for the website theme.
- Use size, spacing, rules, and contrast rather than bold weight to create hierarchy.

Visual asset requirements:

- The first viewport should include a relevant product visual, such as a screenshot-style view of trace timelines, policy decisions, or data-flow visibility.
- Do not use emojis or icons as visual assets.
- Do not use generic stock imagery.
- Do not use abstract gradient blobs, decorative orbs, or bokeh backgrounds.
- The product name and core offer must be visible in the first viewport.

### 19.5 Required Website Sections

The product website should include:

- Header with product name, product links, and primary action
- Hero section with the Agent Capsule name and a clear offer
- Product visual showing trace, policy, or data-flow evidence
- Problem section for private agent debugging
- Workflow section covering Observe, Guard, and Confidential modes
- Privacy review section covering undeclared destinations and CI checks
- Safe trace section covering team collaboration without plaintext payloads
- Confidential demo section for enterprise customer proof of concept
- Multi-language SDK section for Python, TypeScript, Java, Go, and Rust
- Hardware section stating that no specialized local hardware is required for the developer workflow
- Enterprise evidence section showing manifest, policy, attestation, and release identity
- Footer with company, documentation, security, and contact links

### 19.6 Website Content Rules

The website copy must:

- Use direct enterprise language
- Avoid exaggerated claims
- Avoid consumer-style hype
- Avoid emojis
- Avoid icon-led feature lists
- Explain where data remains local
- Explain what the product can and cannot guarantee
- Make hardware requirements clear
- Distinguish local developer workflows from confidential cloud deployment

The website must not imply:

- Agent Capsule guarantees complete AI safety
- Agent Capsule eliminates prompt injection
- Agent Capsule prevents all model extraction
- Confidential mode works without supported cloud infrastructure
- A GPU is required for Agent Capsule itself

### 19.7 Website Run Documentation

The website codebase README must document:

Install dependencies:

```bash
cd agent-capsule-website
pnpm install
```

Run locally:

```bash
pnpm dev
```

Build:

```bash
pnpm build
```

Start production build:

```bash
pnpm start
```

If npm is used:

```bash
npm install
npm run dev
npm run build
npm run start
```

The README must also document:

- Node.js version requirement
- How shadcn/ui was initialized
- How to add shadcn/ui components
- No emoji rule
- No icon rule
- No bold font rule
- Enterprise visual direction
- Website content sections

### 19.8 Website Acceptance Criteria

The product website requirement is satisfied when:

- The website is documented as a separate Next.js and TypeScript codebase.
- shadcn/ui is the required UI system.
- The design requirements explicitly prohibit emojis, icons, and bold fonts.
- The visual direction is enterprise-oriented and restrained.
- The website includes a product-relevant visual in the first viewport.
- The website documents that Agent Capsule does not require specialized local hardware for SDK, CLI, console, safe trace, replay, or policy-check workflows.
- The README runbook includes install, dev, build, and production commands.

## 20. Success Metrics

Developer activation:

- 60% of new projects create their first trace within 15 minutes.
- 40% of traced projects export at least one safe trace within 30 days.
- 30% of traced projects add or update a policy within 30 days.

Console adoption:

- 70% of traced projects open Agent Capsule Console at least once within the first week.
- 60% of console sessions inspect the data-flow graph or privacy map.
- 50% of undeclared destination warnings are resolved from console-generated policy suggestions.

Privacy workflow:

- 90% of undeclared high-risk destinations detected in Observe mode are represented in policy before release builds.
- 80% of policy changes are committed to version control.
- Fewer than 1% of safe trace exports contain plaintext sensitive payloads in automated scanner checks.

Commercial readiness:

- 25% of active teams run `capsule build` within 60 days.
- 10% of active teams create a confidential demo within 90 days.
- Median time to create a customer verification page is under 30 minutes.

Multi-language adoption:

- Python SDK reaches production readiness first.
- TypeScript, Java, Go, and Rust SDKs pass shared trace-schema conformance tests before public beta.
- Cross-language policy checks produce identical results for equivalent traces.

## 21. Release Plan

### Milestone 0: Spec And Prototype

Deliverables:

- Shared trace schema
- Shared policy schema
- Shared manifest schema
- Python SDK prototype
- CLI prototype
- Local encrypted trace store prototype
- Privacy map prototype
- Agent Capsule Console clickable prototype
- Local API bridge prototype
- Product website content outline and design specification

Exit criteria:

- A Python agent can produce a local trace.
- The CLI can detect an undeclared destination.
- The CLI can export a safe trace.
- The console can display a run timeline and data-flow graph from local trace metadata.
- The product website requirements are documented before implementation begins.

### Milestone 1: Python Developer MVP

Deliverables:

- Python SDK
- CLI
- Agent Capsule Console as a separate TypeScript and Next.js frontend
- shadcn/ui component library setup
- Local API bridge for encrypted trace metadata
- Observe mode
- Policy check
- Safe trace export
- Basic replay
- Docker-based capsule build
- Product website as a separate Next.js and shadcn/ui codebase

Exit criteria:

- A real claims-triage sample app can be traced, reviewed, exported, replayed, and packaged.
- The product website can be run locally and communicates private debugging, policy review, safe traces, confidential demos, supported languages, and hardware requirements.

### Milestone 2: Guard Mode And CI

Deliverables:

- Guard mode enforcement
- Field-level redaction
- Human approval workflow
- GitHub Actions integration
- Signed manifest
- CI release checks

Exit criteria:

- A pull request cannot merge when undeclared high-risk egress remains.

### Milestone 3: Multi-Language Beta

Deliverables:

- TypeScript SDK beta
- Java SDK beta
- Go SDK beta
- Rust SDK beta
- Shared conformance test suite
- Cross-language trace fixtures
- Cross-language policy fixtures

Exit criteria:

- Equivalent agent runs in all supported languages produce compatible traces and identical policy decisions.

### Milestone 4: Confidential Demo

Deliverables:

- Confidential demo creation flow
- Verification page
- Attestation result capture
- Secret release integration
- Safe vendor observability
- Sanitized support bundles

Exit criteria:

- A startup can run a private customer POC without receiving plaintext customer data.

### Milestone 5: Enterprise Deployment

Deliverables:

- Customer-cloud install path
- Customer-controlled keys
- Enterprise approval workflow
- Release registry
- Signed usage summaries
- SIEM export
- Update and rollback controls

Exit criteria:

- An enterprise can approve, install, verify, monitor, and update an Agent Capsule in its own environment.

## 22. Risks And Mitigations

Risk: SDK overhead makes developers remove instrumentation.

- Mitigation: Keep instrumentation lightweight, async-safe, and configurable. Provide sampling for metadata while preserving policy-critical events.

Risk: Safe traces are too redacted to be useful.

- Mitigation: Preserve workflow graph, timing, errors, component versions, token counts, payload sizes, hashes, and policy decisions. Provide local-only replay for approved plaintext use.

Risk: Multi-language SDKs drift in behavior.

- Mitigation: Define shared schemas and conformance tests before broad SDK implementation. Require every SDK to pass the same fixtures.

Risk: Policy authoring feels like compliance paperwork.

- Mitigation: Generate policy suggestions from observed behavior, provide copyable diffs, and make CI checks actionable.

Risk: Developers expect full network enforcement that SDK instrumentation cannot guarantee.

- Mitigation: Clearly distinguish SDK-observed egress from runtime-enforced egress. Add stronger enforcement in container and confidential modes.

Risk: Confidential computing requirements slow down MVP.

- Mitigation: Ship local debugging and policy workflows first. Treat confidential demo as an expansion milestone.

Risk: The separate frontend codebase creates product drift from the CLI and SDK.

- Mitigation: Define shared terminology, API contracts, trace fixtures, and UI documentation. Make `capsule view` the canonical entrypoint even when the UI is developed independently.

Risk: The console accidentally exposes sensitive plaintext while trying to improve debugging.

- Mitigation: Render metadata by default, gate plaintext reveal behind explicit local confirmation, audit reveal actions, and add automated UI tests for safe trace and redaction behavior.

Risk: The product website overstates security guarantees.

- Mitigation: Require precise enterprise copy, separate local debugging claims from confidential deployment claims, and include explicit non-goals around AI safety, prompt injection, model extraction, and hardware requirements.

Risk: The product website drifts into a consumer-style landing page.

- Mitigation: Require restrained enterprise visual design, no emojis, no icons, no bold fonts, and product-relevant trace or policy visuals in the first viewport.

## 23. Open Questions

- Which Python agent framework adapter should be first?
- Which model provider SDK should be first?
- Should the production console be served from bundled static assets, a local Next.js server, or an optional desktop wrapper?
- Which graph rendering library should power the data-flow map?
- Should the first product website implementation use bundled product screenshots, generated product mockups, or live-rendered console-style components?
- Which confidential environment should be the first supported target?
- Should policy be authored in YAML only, or should SDK-native policy builders also be supported?
- How should field-level classification work for unstructured prompt strings?
- What is the minimum attestation evidence that an enterprise reviewer will accept for a private demo?
- How should the product price local debugging, team sync, confidential demos, and enterprise deployments?

## 24. MVP Acceptance Criteria

The MVP is ready when:

- A Python developer can install Agent Capsule and trace an existing agent in under 15 minutes.
- Raw prompts, documents, tool payloads, model outputs, and secrets remain local by default.
- Agent Capsule Console runs as a separate TypeScript and Next.js frontend using shadcn/ui.
- Product website requirements are documented as a separate Next.js and shadcn/ui codebase with no emojis, no icons, no bold fonts, and enterprise visual direction.
- `capsule view` opens the console through a localhost-only API bridge.
- The console displays encrypted trace metadata, run timelines, and data-flow visibility without showing raw payloads by default.
- The privacy map detects a new undeclared destination.
- A developer can choose allow, allow selected fields, redact, require approval, or block for that destination.
- Policy changes are written to a version-controlled file.
- `capsule policy check` fails CI when undeclared high-risk egress remains.
- A safe trace can be exported with no plaintext sensitive payloads.
- The safe trace retains enough metadata for a teammate to diagnose a failure.
- `capsule build` creates a signed manifest.
- The shared schemas are stable enough for TypeScript, Java, Go, and Rust SDK implementations.

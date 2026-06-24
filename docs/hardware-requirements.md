# Hardware And Runtime Requirements

Agent Capsule does not require specialized local hardware for the MVP developer workflow.

## No Specialized Local Hardware Required

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
- `capsule demo create` with the local confidential-like provider

## Recommended Local Developer Environment

- CPU: modern 2-core processor minimum, 4-core processor recommended
- Memory: 8 GB RAM minimum, 16 GB RAM recommended for large traces or local agent workloads
- Disk: 1 GB free for SDK, CLI, and console; additional disk depends on trace retention and payload size
- Operating systems: macOS, Linux, and Windows through WSL for MVP
- Network: internet access for external model providers, tool calls, package installation, and optional encrypted team sync
- GPU: not required unless the developer's own agent runs local models
- TPM, Secure Enclave, or local HSM: not required for local development

## Required Software Runtimes

- Python 3.10+ for the Python SDK
- Node.js 20+ for Agent Capsule Console, TypeScript SDK tooling, and product website tooling
- Docker for `capsule build` and container-based local release validation
- Git for version-controlled policies and CI workflows

## Confidential Mode

Confidential mode does not require a special developer machine.

Hosted confidential demonstrations require:

- Supported cloud confidential-computing environment
- Access to the chosen platform's attestation service
- Integrated secrets provider or key-management service

Customer-cloud deployments require the customer's cloud account to support the selected confidential VM, container, enclave, or trusted execution environment.

## Sizing Guidance

Agent Capsule overhead should be small relative to model latency and external tool latency. CPU and memory requirements scale with trace volume, payload metadata size, retention settings, and replay workload. If the agent runs local models, retrieval indexes, OCR, or other compute-heavy tools, those components define the hardware requirement, not Agent Capsule itself.

# Shared Terminology

This terminology must remain consistent across SDKs, CLI, policy engine, console, website, and documentation.

## Agent Capsule

The product and signed artifact used to debug, package, verify, and deploy private AI agents.

## Capsule

The runtime wrapper and release artifact that binds agent metadata, policy, manifest, dependencies, tools, model configuration, network destinations, and usage meters.

## Run

One execution of an instrumented agent workflow. A run contains one trace.

## Trace

The recorded execution graph for a run. A trace contains spans, safe metadata, content hashes, policy decisions, and references to encrypted local payloads.

## Span

A timed unit of work inside a trace. Examples include model call, tool call, retrieval call, database call, approval, or policy decision.

## Destination

Any model provider, tool provider, database, internal service, external domain, or other endpoint that receives data from an agent.

## Data Class

A category of data used for policy decisions. Examples include email, account notes, medical information, secrets, user identifiers, and document text.

## Policy

The version-controlled rules that declare destinations, data classes, allowed fields, redaction rules, human approval requirements, blocking rules, and defaults.

## Policy Decision

The result of evaluating a policy against a model call, tool call, network destination, or payload field. Supported decisions include allow, allow fields, redact, require approval, block, and warn.

## Privacy Map

A view of observed data movement from sources to destinations, including data classes, policy status, risk, and action taken.

## Safe Trace

A shareable trace artifact with plaintext sensitive payloads removed or hashed while retaining workflow structure, timing, versions, errors, token counts, payload sizes, policy decisions, content hashes, and redaction markers.

## Manifest

A signed capsule metadata file containing agent version, runtime version, SDK version, dependency hashes, prompt template hashes, tool definitions, model configuration, policy hash, network destinations, required secrets, usage meters, and signature.

## Observe Mode

Mode that records behavior and detects data movement without blocking execution.

## Guard Mode

Mode that applies policy before supported model calls, tool calls, and network egress. It can warn, redact, require approval, or block.

## Confidential Mode

Mode that runs a packaged agent inside an attested confidential environment and releases protected assets only after verification.


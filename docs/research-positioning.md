# Research-Backed Product Positioning

This note summarizes the product direction behind the current Traceryx demo console.

## Market Pattern

Agent teams already understand observability. Current products and guides focus on multi-step traces, tool calls, retrieval, memory, latency, cost, evaluations, and production debugging:

- LangSmith positions agent observability around step-by-step traces, tool use, retrieval, and non-deterministic execution paths: https://www.langchain.com/resources/agent-observability
- Langfuse positions around tracing, monitoring, evaluation, and testing production agents across common agent frameworks: https://langfuse.com/blog/2024-07-ai-agent-observability-with-langfuse
- Braintrust's 2026 guide frames agent observability as typed spans for tool calls, reasoning, state transitions, and memory operations, connected to evaluation and CI: https://www.braintrust.dev/articles/agent-observability-complete-guide-2026
- MLflow's 2026 observability overview lists tools such as Arize Phoenix and highlights trace analytics, evaluation metrics, and monitoring: https://mlflow.org/top-5-agent-observability-tools/

The category is real, but most products compete on better traces, evals, dashboards, and framework integrations.

## Research Signal

The research direction supports runtime trace capture rather than static review alone. AgentTrace argues that high-stakes agent adoption is limited by security and auditability gaps, and proposes structured runtime telemetry across operational, cognitive, and contextual surfaces: https://arxiv.org/abs/2602.10133

The practical takeaway for Traceryx:

- Capture what the agent did at runtime.
- Preserve workflow structure and policy decisions.
- Avoid requiring reviewers to see private payloads.
- Convert traces into evidence that helps security, engineering, and customer review.

## Risk Signal

Security and governance frameworks point directly at the privacy-evidence wedge:

- OWASP Top 10 for LLM Applications includes sensitive information disclosure, insecure plugin/tool patterns, excessive agency, prompt injection, and related agent risks: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- NIST AI RMF and the Generative AI Profile emphasize AI risk management across data privacy, information security, lifecycle governance, and organizational controls: https://www.nist.gov/itl/ai-risk-management-framework

The practical takeaway:

- Agent teams need evidence that private data did not leak.
- Enterprise buyers need a review artifact before trusting agent workflows.
- CI needs a gate for undeclared high-risk egress.
- Collaboration requires redacted traces that are still useful enough to debug.

## Product Wedge

Traceryx should not try to be a general observability dashboard first. The sharper wedge is:

> Privacy evidence for AI agents: encrypted traces, data-flow visibility, policy review, and share-safe proof for enterprise customers.

This creates a clearer buyer story than "another agent tracing tool":

- Engineering gets live debugging without exposing private logs.
- Security gets a data-flow and policy review artifact.
- Founders selling agents to enterprises get evidence for procurement and proof-of-concept reviews.
- CI gets a release gate when high-risk egress remains undeclared.

## Demo Requirements

The console demo should prove six things in under three minutes:

1. A company is running multiple agents across sensitive workflows.
2. The user can choose a scenario, use the company test matrix to select a risky agent, and run a live agent test, not only inspect static fixture data.
3. The test creates encrypted trace payloads locally.
4. The browser receives safe metadata only: workflow timeline, hashes, data classes, destinations, span counts, token counts, redaction markers, and policy decisions.
5. The reviewer can choose a policy control: allow, allow selected fields, redact, require human approval, or block.
6. The final evidence package and customer verification report are shareable with a teammate, security reviewer, or customer without plaintext prompts, documents, model outputs, tool payloads, secrets, or user identifiers.

## Demo Talk Track

Use this sequence:

1. "This company has ten production-like agents touching claims, support, legal, finance, and risk workflows."
2. "I can choose a scenario, see which agents are riskiest, and run a live privacy test from the console."
3. "The local bridge captures encrypted payloads, but the UI only sees safe metadata."
4. "Now I can see the safe timeline, where data went, which classes moved, and what policy decided."
5. "I can choose the control: allow selected fields, redact, require approval, or block."
6. "Finally, I can export a safe trace, verify the saved package hash, and build a customer report for enterprise review."

## Product Principles

- Show fewer screens with stronger evidence.
- Use plain language: "where data went" instead of "privacy map"; "safe evidence" instead of "compliance artifact."
- Keep raw payload reveal outside the primary path.
- Make run IDs, trace IDs, span counts, finding counts, and destination status visible because they feel concrete.
- Treat CI gates and version-controlled policy as part of the product, not as afterthoughts.
- Make the console useful in fixture mode, but clearly distinguish fixture mode from a bridge-connected live run.

## Near-Term Product Bets

- Add framework adapters for LangChain, OpenAI Agents SDK, LangGraph, CrewAI, and Vercel AI SDK so teams can test existing agents quickly.
- Harden evidence-package export with a signed bundle, policy diff, CI result, and hosted customer verification page.
- Expand the customer-facing verification report into a page that says exactly what was redacted, hashed, blocked, or allowed.
- Add a hosted option later, but keep local-first and private-by-default as the wedge.

# Policy Semantics

This document defines deterministic policy behavior for every SDK and CLI implementation.

## Evaluation Inputs

Policy evaluation receives:

- Policy document
- Destination ID
- Destination risk
- Observed data classes
- Observed payload fields
- Mode: Observe, Guard, or Confidential

Decision output fields must be sorted in ascending lexical order to avoid language-specific set or map ordering differences.

## Decision Precedence

Policy decisions are evaluated in this order:

1. Secrets rule
2. Undeclared high-risk egress rule
3. Undeclared destination rule
4. Destination-specific approval rule
5. Destination-specific redaction rule
6. Destination-specific allowed data rule
7. Allow

The first matching rule wins.

## Actions

Supported actions:

- `allow`: payload may proceed unchanged.
- `allow_fields`: only selected fields may proceed.
- `redact`: configured fields or data classes must be redacted before egress.
- `require_approval`: execution must pause for a human approval decision.
- `block`: call must not execute.
- `warn`: execution may proceed, but warning metadata must be recorded.
- `not_evaluated`: used only for spans that do not involve policy-relevant egress.

## Risk Levels

Risk levels:

- `low`: internal or low-sensitivity destination.
- `medium`: destination may receive operational metadata or limited customer metadata.
- `high`: destination may receive sensitive customer, business, or personal data.
- `critical`: destination may receive secrets, regulated data, or data with contractual restrictions.

Undeclared `high` and `critical` egress must block release builds.

## Data Classes

Initial data classes:

- `account_id`
- `account_notes`
- `address`
- `claimant_name`
- `customer_identifier`
- `document_text`
- `email`
- `incident_description`
- `medical_information`
- `model_output`
- `policy_number`
- `prompt_content`
- `secrets`
- `support_tier`
- `tool_payload`
- `user_identifier`

Implementations may add custom data classes, but built-in classes must retain these names.

## Field-Level Rules

Destination-specific field rules use these lists:

- `allowed_data`: data classes or field names that may leave for this destination.
- `redact`: data classes or field names that must be redacted.
- `require_approval`: data classes or field names that require human approval.

If `allowed_data` is non-empty and observed fields include values outside the allowlist, the decision is `allow_fields` unless a higher-precedence rule matches.

If observed fields intersect `redact`, the decision is `redact` unless a higher-precedence rule matches.

If observed fields or data classes intersect `require_approval`, the decision is `require_approval` unless a higher-precedence rule matches.

## Default Rules

Policy defaults define behavior for:

- `undeclared_high_risk_egress`
- `undeclared_destination`
- `secrets`

The MVP default should be:

```json
{
  "undeclared_high_risk_egress": "block",
  "undeclared_destination": "warn",
  "secrets": "block"
}
```

## Observe Mode

Observe mode records decisions but does not block execution.

If a decision would block in Guard mode, Observe mode records:

- `action`: `warn`
- `reason`: original blocking reason prefixed with `observe_only:`

## Privacy Map

Phase 5 generates a privacy map from trace metadata and policy documents.

The privacy map records:

- Declared and undeclared destinations
- Destination risk and computed egress risk
- Observed data classes
- Policy actions observed for each destination
- Findings such as `undeclared_destination` and `undeclared_high_risk_egress`
- Suggested policy actions: allow, allow fields, redact, require approval, or block

Privacy maps must not read encrypted payload sidecars or include plaintext payload values.

## CI Gate

`capsule policy check --fail-on high-risk-egress` must return a non-zero exit code when an undeclared destination has high or critical egress risk.

## Guard Mode

Guard mode enforces policy decisions before supported egress.

Guard mode must:

- Redact before egress for `redact`.
- Remove disallowed classified fields before egress for `allow_fields`.
- Pause before egress for `require_approval`.
- Prevent egress for `block`.
- Record every decision in the trace.

Python approval handlers receive safe request metadata only: run ID, trace ID, span ID, component name, destination ID, policy reason, fields, policy version, content hash, and payload size. They must not receive plaintext prompt, document, model-output, or tool payload values.

## Confidential Mode

Confidential mode must enforce Guard mode behavior and require environment verification before protected assets or secrets are released.

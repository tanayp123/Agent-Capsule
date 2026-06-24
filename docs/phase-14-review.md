# Phase 14 Review: Confidential Demo

## Scope Reviewed

- Added `capsule demo create --customer <id> --mode confidential`.
- Required signed manifests and supported release runtimes.
- Required policy hash/version match between manifest and selected policy.
- Blocked demos when supplied traces contain undeclared destinations or undeclared high-risk egress.
- Added local confidential-like environment startup metadata.
- Captured attestation results.
- Released only required secret names after verification.
- Generated customer verification pages.
- Generated safe vendor telemetry.
- Generated sanitized support bundles on failure.

## Attestation Assumptions

Phase 14 implements a local confidential-like provider named `local-confidential-like`. It validates the Confidential mode control flow but does not claim hosted confidential hardware. Hosted confidential environments in later phases must replace this provider with platform attestation evidence.

Attestation passes only when:

- Provider is supported.
- Status is `verified`.
- Manifest hash matches when supplied.
- Runtime version matches when supplied.

## Secret Release Review

Secrets are released only after preflight and attestation pass. The CLI records secret names, missing names, receipt hash, and release status. It rejects `--secret NAME=VALUE` style input and does not record secret values.

## Customer Verification Page

The verification page shows:

- Customer and capsule identity.
- Manifest hash without manifest signature value.
- Runtime language and version.
- Attestation provider, status, and evidence hash.
- Approved model providers, tools, and network destinations.
- Policy version and data class rules.
- Secret release provider, released status, secret names, and receipt hash.
- Finding codes and messages when blocked.

## Vendor Telemetry Review

Vendor telemetry is limited to safe metadata: health, component versions, environment metadata, attestation status, secret release receipt metadata, usage meters, and safe trace span summaries. It does not decrypt raw payload sidecars.

## Sanitized Support Bundle Review

Support bundles include findings, safe manifest metadata, safe policy metadata, environment metadata, attestation metadata, secret release metadata, and artifact paths. They explicitly mark raw payloads, secret values, and manifest signature values as excluded.

## Verification

Run:

```bash
bash ci/check-phase14.sh
```

This runs previous phase checks, CLI tests, successful demo creation, failed attestation, missing secrets, policy failure, and artifact leakage checks.

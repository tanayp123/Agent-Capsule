# Phase 11 Review

## Scope Reviewed

- `capsule build` signed manifest generation.
- Policy validation before manifest creation.
- Dependency lockfile, prompt template, tool schema, model configuration, policy, network destination, required secret, and usage-meter capture.
- Safe `capsule manifest inspect` behavior.
- Manifest signature, reproducibility, dependency-change detection, and malformed-manifest handling.
- Phase 11 CI checks.

## Review Findings And Fixes

- Manifest inspection previously accepted missing signatures. It now validates required manifest fields and fails when `signature.value` is absent.
- `capsule build` signs canonical manifest content with HMAC-SHA256 and stores only the signature value in the manifest, never in build or inspect output.
- Prompt templates and model config files are hashed only; their plaintext is not serialized into the manifest or build report.
- Repeated builds with identical inputs and signing key are reproducible. Dependency lockfile changes alter both dependency hashes and the manifest signature.
- Malformed manifest JSON now returns a safe validation error instead of throwing a traceback.

## Security Checklist

- Policy: build validates the policy before emitting a manifest.
- Signing: signature is computed over canonical manifest content with an empty signature value field.
- Dependency hashes: known lockfiles are discovered, and explicit lockfiles are supported.
- Prompt templates: build records hash by template name only.
- Tool schemas: build records name, version, and schema hash only.
- Inspect output: signature value is never printed.

## Residual Risk

- Phase 11 uses local HMAC signing for developer builds. Later release phases should add stronger key lifecycle controls and customer-verifiable signature policy.
- Container image building is not implemented in Phase 11; the CLI records a supplied `--container-digest` or `AGENT_CAPSULE_CONTAINER_DIGEST` when available.

## Verification

- `python3 -m unittest cli/tests/test_cli.py`
- `bash ci/check-phase11.sh`

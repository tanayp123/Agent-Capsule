# Confidential Demo

`capsule demo create` prepares a private customer proof of concept from safe Agent Capsule evidence. The Phase 14 implementation uses a local confidential-like provider by default. It validates the Confidential mode workflow without claiming that local execution is a hosted confidential-computing environment.

## Command

```bash
source ci/python-env.sh
export PYTHONPATH="$PWD/cli/src:$PYTHONPATH"
python3 -m agent_capsule_cli demo create \
  --customer acme-insurance \
  --mode confidential \
  --manifest .agent-capsule/manifests/capsule-manifest.json \
  --policy agent-capsule.policy.yaml \
  --trace-dir .agent-capsule/traces \
  --secret MODEL_PROVIDER_API_KEY \
  --secret CRM_API_KEY \
  --output-dir .agent-capsule/demos
```

## Gates

The command exits nonzero when any required gate fails:

- A signed manifest is missing or invalid.
- The manifest runtime is unsupported for release-style Confidential mode.
- The manifest policy hash or policy version does not match the selected policy file.
- The manifest and policy disagree about declared network destinations.
- Supplied traces contain undeclared destinations or undeclared high-risk egress.
- Attestation evidence is missing, failed, mismatched, or from an unsupported provider.
- Manifest-required secret names are not configured for release.

Secrets are released only after preflight and attestation verification pass. The CLI accepts secret names with `--secret`; it rejects secret values.

## Artifacts

Artifacts are written under `.agent-capsule/demos/<customer>/` by default:

- `attestation-result.json`: safe attestation result with provider, status, runtime metadata, manifest hash, and evidence hash.
- `customer-verification.html`: customer-facing page showing capsule identity, attestation status, approved model providers, approved tools, approved network destinations, policy version, data class rules, and secret release receipt hash.
- `vendor-telemetry.json`: safe vendor observability metadata including health, component versions, timing-safe trace summaries, payload sizes, token counts, policy decisions, usage meters, and finding codes.
- `support-bundle.json`: written on failure with sanitized troubleshooting context.

These artifacts do not contain prompt content, document text, model outputs, tool payloads, secret values, user identifiers, or manifest signature values.

## Attestation Evidence

Pass explicit evidence with:

```bash
python3 -m agent_capsule_cli demo create \
  --customer acme-insurance \
  --manifest .agent-capsule/manifests/capsule-manifest.json \
  --policy agent-capsule.policy.yaml \
  --attestation-evidence attestation.json
```

Supported Phase 14 evidence fields:

```json
{
  "provider": "local-confidential-like",
  "status": "verified",
  "manifest_hash": "sha256:<manifest-file-hash>",
  "runtime_language": "python",
  "runtime_version": "3.10.14"
}
```

If `manifest_hash` or `runtime_version` is present, it must match the selected manifest.

## Secret Release Providers

Phase 14 supports:

- `manual`: pass configured secret names with `--secret NAME`.
- `env`: required secret names must exist as environment variables.
- `none`: no secrets are configured.

The release receipt records secret names, missing names, release status, attestation evidence hash, and a receipt hash. It never records secret values.

## Verification

Run:

```bash
bash ci/check-phase14.sh
```

The check covers successful demo creation, failed attestation, missing secrets, policy failure, safe vendor telemetry, customer verification generation, and support bundle sanitization.

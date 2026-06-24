# Policy Engine

Purpose: deterministic privacy policy evaluation for SDKs, CLI, CI, and Agent Capsule Console.

Phase 5 status: Python MVP implemented.

Implemented features:

- Policy parsing
- Policy validation
- Destination registry
- Data-class matching
- Risk classification
- Actions: allow, allow selected fields, redact, require approval, block, warn
- Undeclared destination detection
- Undeclared high-risk egress detection
- Policy suggestions for allow, allow fields, redact, require approval, and block
- Privacy-map generation from trace metadata
- CI-compatible decision output

## Run Locally

From the repository root:

```bash
source ci/python-env.sh
python3 -m unittest discover -s policy-engine/tests -p 'test_*.py'
```

Run the complete phase gate:

```bash
bash ci/check-phase5.sh
```

## Privacy Map

The privacy map is generated from trace metadata and policy documents. It includes destination IDs, domains, declared status, risk, observed data classes, policy actions, findings, and suggested policy patches. It does not read or decrypt encrypted payload sidecars.

#!/usr/bin/env bash
set -euo pipefail

required_paths=(
  "PRD.md"
  "agent.md"
  "README.md"
  ".editorconfig"
  ".gitignore"
  ".github/workflows/ci.yml"
  "ci/README.md"
  "docs/development.md"
  "docs/tooling.md"
  "docs/coding-standards.md"
  "docs/terminology.md"
  "docs/security-baseline.md"
  "docs/hardware-requirements.md"
  "docs/phase-0-review.md"
  "schemas/README.md"
  "fixtures/README.md"
  "fixtures/traces/README.md"
  "fixtures/policies/README.md"
  "fixtures/manifests/README.md"
  "fixtures/safe-traces/README.md"
  "cli/README.md"
  "sdk-python/README.md"
  "sdk-typescript/README.md"
  "sdk-java/README.md"
  "sdk-go/README.md"
  "sdk-rust/README.md"
  "policy-engine/README.md"
  "trace-store/README.md"
  "local-api/README.md"
  "agent-capsule-console/README.md"
  "agent-capsule-website/README.md"
  "examples/README.md"
  "examples/claims-triage-python/README.md"
)

missing=0

for path in "${required_paths[@]}"; do
  if [[ ! -e "$path" ]]; then
    echo "Missing required Phase 0 path: $path"
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

echo "Phase 0 foundation check passed."


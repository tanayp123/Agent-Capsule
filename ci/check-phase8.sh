#!/usr/bin/env bash
set -euo pipefail

bash ci/check-phase7.sh

(
  cd agent-capsule-console
  npm ci
  npm audit --audit-level=moderate
  npm run build
  npx playwright install chromium
  npm run test:ui
)

echo "Phase 8 console checks passed."

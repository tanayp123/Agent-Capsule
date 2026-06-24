#!/usr/bin/env bash
set -euo pipefail

bash ci/check-foundation.sh
python3 ci/validate-phase1.py

echo "Phase 1 schema and conformance checks passed."


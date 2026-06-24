#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

bash ci/check-phase12.sh
source ci/python-env.sh
export PYTHONPATH="$repo_root/cli/src:$PYTHONPATH"

(
  cd sdk-typescript
  npm ci
  npm run typecheck
  npm test
)

if javac -version >/dev/null 2>&1 && java -version >/dev/null 2>&1; then
  rm -rf sdk-java/build
  mkdir -p sdk-java/build/classes
  find sdk-java/src/main/java sdk-java/src/test/java -name '*.java' | sort > sdk-java/build/sources.txt
  javac -d sdk-java/build/classes @sdk-java/build/sources.txt
  java -cp sdk-java/build/classes dev.agentcapsule.ConformanceTest
else
  echo "Skipping Java native tests because a JDK is not installed."
fi

if command -v go >/dev/null 2>&1; then
  (cd sdk-go && go test ./...)
else
  echo "Skipping Go native tests because Go is not installed."
fi

if command -v cargo >/dev/null 2>&1; then
  (cd sdk-rust && cargo test)
else
  echo "Skipping Rust native tests because Cargo is not installed."
fi

python3 ci/validate-phase13.py

echo "Phase 13 multi-language SDK beta checks passed."

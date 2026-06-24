#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

bash ci/check-phase14.sh

(
  cd agent-capsule-website
  npm ci
  npm run build
  npm test
)

if rg -n "lucide-react|<svg|data-lucide|className=.*icon|font-bold|font-semibold|font-extrabold|font-weight:\\s*[5-9]00" agent-capsule-website/app agent-capsule-website/components agent-capsule-website/lib agent-capsule-website/README.md; then
  echo "Product website violates no-icon or no-bold-font rules." >&2
  exit 1
fi

python3 - <<'PY'
import sys
import unicodedata
from pathlib import Path

paths = [
    *Path("agent-capsule-website/app").rglob("*"),
    *Path("agent-capsule-website/components").rglob("*"),
    Path("agent-capsule-website/README.md"),
]
for path in paths:
    if not path.is_file() or path.suffix not in {".tsx", ".ts", ".css", ".md"}:
        continue
    text = path.read_text(encoding="utf-8")
    for char in text:
        if ord(char) < 128:
            continue
        if unicodedata.category(char) in {"So", "Sk"}:
            print(f"emoji-like symbol found in {path}: {char!r}", file=sys.stderr)
            raise SystemExit(1)
PY

echo "Phase 15 product website checks passed."

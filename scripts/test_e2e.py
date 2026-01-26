#!/usr/bin/env python3
"""
scripts.test_e2e

End-to-end sanity checks for the paper repository artifacts:
1) schema/xshield_schema.json parses as JSON
2) all schema/examples/*.json validate against the schema
3) JSON blocks in study/vignettes.md parse, and X-SHIELD blocks validate

Usage:
  python3 scripts/test_e2e.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> int:
    """Run a command, streaming output; return exit code."""
    print(f"\n$ {' '.join(cmd)}")
    p = subprocess.run(cmd)
    return int(p.returncode)


def main() -> int:
    """Run all checks; exit non-zero if any fails."""
    root = Path(__file__).resolve().parents[1]

    # 1) Schema parse check
    code = run([
        sys.executable,
        "-c",
        "import json; json.load(open('schema/xshield_schema.json','r',encoding='utf-8')); print('OK schema JSON')"
    ])
    if code != 0:
        return code

    # 2) Examples validate
    code = run([sys.executable, str(root / "scripts" / "validate_schema_examples.py")])
    if code != 0:
        return code

    # 3) Vignettes validate
    code = run([sys.executable, str(root / "scripts" / "validate_vignettes.py")])
    if code != 0:
        return code

    print("\n✅ E2E checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


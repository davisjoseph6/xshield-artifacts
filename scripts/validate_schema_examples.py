#!/usr/bin/env python3
"""
scripts.validate_schema_examples

Validate all JSON files under schema/examples/ against schema/xshield_schema.json.

Usage:
  python3 scripts/validate_schema_examples.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


def load_json(path: Path) -> dict:
    """Load a JSON file as a Python dict."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    """Run example validations and return process exit code."""
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "schema" / "xshield_schema.json"
    examples_dir = root / "schema" / "examples"

    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)

    failures: list[str] = []
    for p in sorted(examples_dir.glob("*.json")):
        data = load_json(p)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            msg_lines = [f"[FAIL] {p.relative_to(root)}"]
            for err in errors:
                loc = "/".join(str(x) for x in err.path)
                msg_lines.append(f"  - at '{loc or '<root>'}': {err.message}")
            failures.append("\n".join(msg_lines))
        else:
            print(f"[OK]   {p.relative_to(root)}")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    print("\nAll example files validated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


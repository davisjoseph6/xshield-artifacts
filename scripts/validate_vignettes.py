#!/usr/bin/env python3
"""
scripts.validate_vignettes

Extract JSON code blocks from study/vignettes.md.
- Ensure each JSON block parses.
- Validate blocks that contain "schema_version" against schema/xshield_schema.json.

Usage:
  python3 scripts/validate_vignettes.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def load_json(path: Path) -> dict:
    """Load a JSON file as a Python dict."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    """Validate JSON blocks in the vignette markdown."""
    root = Path(__file__).resolve().parents[1]
    vignette_path = root / "study" / "vignettes.md"
    schema_path = root / "schema" / "xshield_schema.json"

    text = vignette_path.read_text(encoding="utf-8")
    blocks = JSON_BLOCK_RE.findall(text)

    if not blocks:
        print("[WARN] No ```json blocks found in study/vignettes.md", file=sys.stderr)
        return 1

    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)

    failed = False
    for i, raw in enumerate(blocks, start=1):
        raw = raw.strip()
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            failed = True
            print(f"[FAIL] Block #{i}: invalid JSON: {e}", file=sys.stderr)
            continue

        # Only validate blocks that look like X-SHIELD objects
        if isinstance(obj, dict) and "schema_version" in obj:
            errors = sorted(validator.iter_errors(obj), key=lambda e: e.path)
            if errors:
                failed = True
                print(f"[FAIL] Block #{i}: schema validation failed", file=sys.stderr)
                for err in errors:
                    loc = "/".join(str(x) for x in err.path)
                    print(f"  - at '{loc or '<root>'}': {err.message}", file=sys.stderr)
            else:
                print(f"[OK]   Block #{i}: schema-valid X-SHIELD JSON")
        else:
            print(f"[OK]   Block #{i}: parsed JSON (baseline/unstructured)")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


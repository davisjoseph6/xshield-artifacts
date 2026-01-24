#!/usr/bin/env python3
"""Validate generated X-SHIELD outputs against the JSON Schema (draft 2020-12)."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "schema" / "xshield_schema.json"
    out_dir = root / "data" / "xshield_outputs"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    files = sorted(out_dir.glob("*_xshield.json"))
    if not files:
        raise SystemExit(f"No *_xshield.json files found in {out_dir}")

    failed = False
    for fp in files:
        data = json.loads(fp.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            failed = True
            print(f"\nSCHEMA FAIL: {fp.name}")
            for e in errors[:10]:
                path = ".".join(str(p) for p in e.path) or "<root>"
                print(f"  - {path}: {e.message}")

    if failed:
        print("\nSchema validation FAILED.")
        return 1

    print("Schema validation OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


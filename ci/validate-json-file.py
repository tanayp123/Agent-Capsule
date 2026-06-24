#!/usr/bin/env python3
import json
import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().with_name("validate-phase1.py")
SPEC = importlib.util.spec_from_file_location("validate_phase1", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load validate-phase1.py")
validate_phase1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_phase1)

ValidationError = validate_phase1.ValidationError
load_json = validate_phase1.load_json
validate = validate_phase1.validate


def main():
    if len(sys.argv) != 3:
        print("usage: validate-json-file.py <schema> <json-file>", file=sys.stderr)
        return 2

    schema_path = sys.argv[1]
    json_path = Path(sys.argv[2])
    schema = load_json(schema_path)
    value = json.loads(json_path.read_text(encoding="utf-8"))

    try:
        validate(schema, value)
    except ValidationError as exc:
        print("%s failed %s: %s" % (json_path, schema_path, exc), file=sys.stderr)
        return 1

    print("%s validates against %s" % (json_path, schema_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

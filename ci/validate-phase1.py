#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "policy-engine" / "src"))

from policy_engine import evaluate_policy as engine_evaluate_policy  # noqa: E402
from policy_engine import load_policy_file  # noqa: E402

SCHEMA_FIXTURES = {
    "schemas/destination.schema.json": ["fixtures/destinations/*.json"],
    "schemas/trace.schema.json": ["fixtures/traces/*.json"],
    "schemas/policy.schema.json": ["fixtures/policies/*.json"],
    "schemas/safe-trace.schema.json": ["fixtures/safe-traces/*.json"],
    "schemas/manifest.schema.json": ["fixtures/manifests/*.json"],
}

SENSITIVE_SAFE_TRACE_KEYS = {
    "raw_payload",
    "prompt",
    "document_text",
    "model_output",
    "tool_payload",
    "secret",
    "api_key",
    "access_token",
}


class ValidationError(Exception):
    pass


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def type_matches(value, expected_type):
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return False


def validate(schema, value, path="$"):
    if "const" in schema and value != schema["const"]:
        raise ValidationError("%s expected const %r" % (path, schema["const"]))

    if "enum" in schema and value not in schema["enum"]:
        raise ValidationError("%s expected one of %r, got %r" % (path, schema["enum"], value))

    if "type" in schema:
        expected = schema["type"]
        expected_types = expected if isinstance(expected, list) else [expected]
        if not any(type_matches(value, item) for item in expected_types):
            raise ValidationError("%s expected type %r, got %s" % (path, expected, type(value).__name__))

    if value is None:
        return

    if isinstance(value, str) and "pattern" in schema:
        if not re.match(schema["pattern"], value):
            raise ValidationError("%s does not match pattern %s" % (path, schema["pattern"]))

    if isinstance(value, int) and "minimum" in schema:
        if value < schema["minimum"]:
            raise ValidationError("%s expected minimum %s" % (path, schema["minimum"]))

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ValidationError("%s expected at least %s items" % (path, schema["minItems"]))
        if "items" in schema:
            for index, item in enumerate(value):
                validate(schema["items"], item, "%s[%s]" % (path, index))

    if isinstance(value, dict):
        for required_key in schema.get("required", []):
            if required_key not in value:
                raise ValidationError("%s missing required key %s" % (path, required_key))

        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)

        for key, item in value.items():
            if key in properties:
                validate(properties[key], item, "%s.%s" % (path, key))
            elif additional is False:
                raise ValidationError("%s unexpected key %s" % (path, key))
            elif isinstance(additional, dict):
                validate(additional, item, "%s.%s" % (path, key))


def validate_schemas_and_fixtures():
    errors = []

    for schema_path, patterns in SCHEMA_FIXTURES.items():
        try:
            schema = load_json(schema_path)
        except Exception as exc:
            errors.append("%s failed to load: %s" % (schema_path, exc))
            continue

        for key in ("$schema", "$id", "title", "type", "properties"):
            if key not in schema:
                errors.append("%s missing schema key %s" % (schema_path, key))

        fixture_paths = []
        for pattern in patterns:
            fixture_paths.extend(sorted(ROOT.glob(pattern)))

        if not fixture_paths:
            errors.append("%s has no fixtures" % schema_path)

        for fixture_path in fixture_paths:
            relative_fixture = fixture_path.relative_to(ROOT)
            try:
                fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
                validate(schema, fixture, "$")
            except Exception as exc:
                errors.append("%s failed %s: %s" % (relative_fixture, schema_path, exc))

    return errors


def evaluate_policy(policy, destination_id, destination_risk, data_classes, fields):
    data_classes = set(data_classes)
    fields = set(fields)

    if "secrets" in data_classes:
        return {
            "action": policy["defaults"]["secrets"],
            "fields": sorted(fields),
            "reason": "secrets default rule matched",
        }

    destination = policy["destinations"].get(destination_id)
    if destination is None:
        if destination_risk in ("high", "critical"):
            return {
                "action": policy["defaults"]["undeclared_high_risk_egress"],
                "fields": sorted(fields),
                "reason": "undeclared high-risk egress",
            }
        return {
            "action": policy["defaults"]["undeclared_destination"],
            "fields": sorted(fields),
            "reason": "undeclared destination",
        }

    approval = set(destination["require_approval"])
    if data_classes.intersection(approval) or fields.intersection(approval):
        matched = sorted((data_classes | fields).intersection(approval))
        return {
            "action": "require_approval",
            "fields": matched,
            "reason": "destination approval rule matched",
        }

    redact = set(destination["redact"])
    if data_classes.intersection(redact) or fields.intersection(redact):
        matched = sorted((data_classes | fields).intersection(redact))
        return {
            "action": "redact",
            "fields": matched,
            "reason": "destination redaction rule matched",
        }

    allowed = set(destination["allowed_data"])
    if allowed and not data_classes.union(fields).issubset(allowed):
        return {
            "action": "allow_fields",
            "fields": sorted(allowed),
            "reason": "destination allowed fields rule matched",
        }

    return {
        "action": "allow",
        "fields": sorted(fields),
        "reason": "destination declared and data allowed",
    }


def validate_policy_conformance():
    errors = []
    fixture = load_json("fixtures/conformance/policy-decisions.json")

    for case in fixture["cases"]:
        policy = load_policy_file(ROOT / case["policy"])
        decision = engine_evaluate_policy(
            policy=policy,
            destination_id=case["destination_id"],
            destination_risk=case["destination_risk"],
            data_classes=case["data_classes"],
            fields=case["fields"],
        )
        actual = {
            "action": decision.action,
            "fields": list(decision.fields),
            "reason": decision.reason,
        }
        expected = case["expected"]
        if actual != expected:
            errors.append(
                "%s expected %s but got %s" % (case["name"], json.dumps(expected), json.dumps(actual))
            )

    return errors


def scan_safe_traces():
    errors = []
    for safe_trace_path in sorted((ROOT / "fixtures/safe-traces").glob("*.json")):
        safe_trace = json.loads(safe_trace_path.read_text(encoding="utf-8"))
        stack = [("$", safe_trace)]
        while stack:
            path, value = stack.pop()
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in SENSITIVE_SAFE_TRACE_KEYS:
                        errors.append("%s contains reserved sensitive key %s" % (safe_trace_path, key))
                    stack.append(("%s.%s" % (path, key), child))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    stack.append(("%s[%s]" % (path, index), child))
    return errors


def main():
    errors = []
    errors.extend(validate_schemas_and_fixtures())
    errors.extend(validate_policy_conformance())
    errors.extend(scan_safe_traces())

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("Validated schemas, fixtures, policy conformance, and safe trace scanner.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

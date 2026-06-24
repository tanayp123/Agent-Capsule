#!/usr/bin/env python3
import importlib.util
import json
import sys
from pathlib import Path

from policy_engine import evaluate_policy, generate_privacy_map, load_policy_file


ROOT = Path(__file__).resolve().parents[1]
TRACE_FIXTURES = {
    "typescript": ROOT / "fixtures/conformance/traces/typescript-claims-trace.json",
    "java": ROOT / "fixtures/conformance/traces/java-claims-trace.json",
    "go": ROOT / "fixtures/conformance/traces/go-claims-trace.json",
    "rust": ROOT / "fixtures/conformance/traces/rust-claims-trace.json",
}
RAW_STRINGS = [
    "claimant@example.com",
    "Sensitive account note",
    "Sensitive note",
    "private diagnosis",
    "private document",
]


def main() -> int:
    validate_phase1 = load_phase1_validator()
    trace_schema = load_json(ROOT / "schemas/trace.schema.json")
    validate_policy_decisions()
    signatures = {}
    privacy_signatures = {}

    for language, path in TRACE_FIXTURES.items():
        trace = load_json(path)
        validate_phase1.validate(trace_schema, trace)
        assert trace["language"] == language, "%s language mismatch" % path
        assert_no_plaintext(path)
        signatures[language] = trace_signature(trace)
        privacy_signatures[language] = privacy_signature(trace)

    expected_signature = next(iter(signatures.values()))
    for language, signature in signatures.items():
        assert signature == expected_signature, "%s trace semantics drifted" % language

    expected_privacy = next(iter(privacy_signatures.values()))
    for language, signature in privacy_signatures.items():
        assert signature == expected_privacy, "%s privacy map semantics drifted" % language

    print("Phase 13 cross-language conformance fixtures passed.")
    return 0


def validate_policy_decisions() -> None:
    fixture = load_json(ROOT / "fixtures/conformance/policy-decisions.json")
    for item in fixture["cases"]:
        policy = load_policy_file(ROOT / item["policy"])
        decision = evaluate_policy(
            policy,
            destination_id=item["destination_id"],
            destination_risk=item["destination_risk"],
            data_classes=item["data_classes"],
            fields=item["fields"],
            mode="guard",
        )
        expected = item["expected"]
        assert decision.action == expected["action"], item["name"]
        assert list(decision.fields) == expected["fields"], item["name"]
        assert decision.reason == expected["reason"], item["name"]


def trace_signature(trace: dict) -> dict:
    spans = [
        {
            "component_type": span["component_type"],
            "component_name": span["component_name"],
            "status": span["status"],
            "destination_id": span["destination_id"],
            "data_classes": sorted(span["data_classes"]),
            "policy_action": span["policy_decision"]["action"],
            "policy_reason": span["policy_decision"]["reason"],
            "policy_fields": sorted(span["policy_decision"]["fields"]),
        }
        for span in trace["spans"]
    ]
    destinations = [
        {
            "id": destination["id"],
            "type": destination["type"],
            "domain": destination["domain"],
            "risk": destination["risk"],
            "declared_in_policy": destination["declared_in_policy"],
            "allowed_data_classes": sorted(destination["allowed_data_classes"]),
            "observed_data_classes": sorted(destination["observed_data_classes"]),
        }
        for destination in trace["destinations"]
    ]
    return {
        "agent": trace["agent"],
        "mode": trace["mode"],
        "spans": spans,
        "destinations": destinations,
    }


def privacy_signature(trace: dict) -> dict:
    policy = load_policy_file(ROOT / "fixtures/policies/crm-policy.json")
    privacy_map = generate_privacy_map(trace, policy)
    return {
        "destinations": [
            {
                "id": destination["id"],
                "declared_in_policy": destination["declared_in_policy"],
                "egress_risk": destination["egress_risk"],
                "observed_data_classes": sorted(destination["observed_data_classes"]),
                "actions": sorted(destination["actions"]),
                "findings": sorted(destination["findings"]),
            }
            for destination in privacy_map["destinations"]
        ],
        "findings": privacy_map["findings"],
    }


def assert_no_plaintext(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for raw in RAW_STRINGS:
        assert raw not in text, "%s leaked plaintext %s" % (path, raw)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_phase1_validator():
    module_path = ROOT / "ci/validate-phase1.py"
    spec = importlib.util.spec_from_file_location("validate_phase1", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load validate-phase1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print("Phase 13 validation failed: %s" % exc, file=sys.stderr)
        raise SystemExit(1)

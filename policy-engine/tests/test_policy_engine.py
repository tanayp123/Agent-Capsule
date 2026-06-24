import json
import tempfile
import unittest
from pathlib import Path

from policy_engine import (
    PolicyEngineError,
    classify_egress_risk,
    evaluate_policy,
    generate_privacy_map,
    load_policy_file,
)


ROOT = Path(__file__).resolve().parents[2]
CRM_POLICY = ROOT / "fixtures" / "policies" / "crm-policy.json"
RESTRICTIVE_POLICY = ROOT / "fixtures" / "policies" / "restrictive-policy.json"
CRM_TRACE = ROOT / "fixtures" / "traces" / "crm-privacy-review.json"


class PolicyEngineTests(unittest.TestCase):
    def test_conformance_fixture_decisions_are_deterministic(self):
        conformance = json.loads((ROOT / "fixtures" / "conformance" / "policy-decisions.json").read_text())
        for case in conformance["cases"]:
            policy = load_policy_file(ROOT / case["policy"])
            decision = evaluate_policy(
                policy=policy,
                destination_id=case["destination_id"],
                destination_risk=case["destination_risk"],
                data_classes=case["data_classes"],
                fields=case["fields"],
            )
            self.assertEqual(decision.to_trace_dict()["action"], case["expected"]["action"], case["name"])
            self.assertEqual(decision.to_trace_dict()["fields"], case["expected"]["fields"], case["name"])
            self.assertEqual(decision.to_trace_dict()["reason"], case["expected"]["reason"], case["name"])

    def test_allow_fields_when_observed_data_exceeds_allowlist(self):
        policy = load_policy_file(CRM_POLICY)
        decision = evaluate_policy(
            policy,
            destination_id="crm",
            destination_risk="high",
            data_classes=["account_id", "email"],
            fields=["account_id", "email"],
        )
        self.assertEqual(decision.action, "redact")
        self.assertEqual(decision.fields, ("email",))

        policy["destinations"]["crm"]["redact"] = []
        decision = evaluate_policy(
            policy,
            destination_id="crm",
            destination_risk="high",
            data_classes=["account_id", "email"],
            fields=["account_id", "email"],
        )
        self.assertEqual(decision.action, "allow_fields")
        self.assertEqual(decision.fields, ("account_id",))

    def test_observe_mode_turns_block_into_warning(self):
        policy = load_policy_file(RESTRICTIVE_POLICY)
        decision = evaluate_policy(
            policy,
            destination_id="crm",
            destination_risk="high",
            data_classes=["email", "account_notes"],
            mode="observe",
        )
        self.assertEqual(decision.action, "warn")
        self.assertEqual(decision.reason, "observe_only: undeclared high-risk egress")

    def test_privacy_map_detects_undeclared_crm_and_suggests_actions(self):
        policy = load_policy_file(RESTRICTIVE_POLICY)
        trace = json.loads(CRM_TRACE.read_text(encoding="utf-8"))
        privacy_map = generate_privacy_map(trace, policy)

        destination = privacy_map["destinations"][0]
        self.assertEqual(destination["id"], "crm")
        self.assertFalse(destination["declared_in_policy"])
        self.assertIn("email", destination["observed_data_classes"])
        self.assertIn("undeclared_destination", destination["findings"])
        self.assertIn("undeclared_high_risk_egress", destination["findings"])

        findings = {finding["kind"] for finding in privacy_map["findings"]}
        self.assertIn("undeclared_high_risk_egress", findings)
        suggestion_actions = {item["action"] for item in privacy_map["policy_suggestions"]}
        self.assertEqual(
            suggestion_actions,
            {"allow", "allow_fields", "redact", "require_approval", "block"},
        )

    def test_yaml_policy_parser_supports_generated_init_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy_path = Path(tmp) / "agent-capsule.policy.yaml"
            policy_path.write_text(
                """version: 1
agent:
  name: claims-triage
  owner: platform-team
destinations: {}
defaults:
  undeclared_high_risk_egress: block
  undeclared_destination: warn
  secrets: block
""",
                encoding="utf-8",
            )
            policy = load_policy_file(policy_path)
            self.assertEqual(policy["version"], 1)
            self.assertEqual(policy["destinations"], {})

    def test_yaml_policy_parser_supports_destination_lists(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy_path = Path(tmp) / "agent-capsule.policy.yaml"
            policy_path.write_text(
                """version: 1
agent:
  name: claims-triage
  owner: platform-team
destinations:
  crm:
    type: external_tool
    domain: api.crm.example
    risk: high
    allowed_data:
      - account_id
      - support_tier
    redact:
      - email
      - account_notes
    require_approval:
      - medical_information
defaults:
  undeclared_high_risk_egress: block
  undeclared_destination: warn
  secrets: block
""",
                encoding="utf-8",
            )
            policy = load_policy_file(policy_path)
            self.assertEqual(policy["destinations"]["crm"]["allowed_data"], ["account_id", "support_tier"])
            self.assertEqual(policy["destinations"]["crm"]["redact"], ["account_notes", "email"])

    def test_invalid_policy_reports_validation_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy_path = Path(tmp) / "bad.json"
            policy_path.write_text('{"version": 1}', encoding="utf-8")
            with self.assertRaises(PolicyEngineError) as raised:
                load_policy_file(policy_path)
            self.assertIn("invalid policy", str(raised.exception))

    def test_risk_classification_uses_destination_and_data_risk(self):
        self.assertEqual(classify_egress_risk("low", ["secrets"]), "critical")
        self.assertEqual(classify_egress_risk("high", ["support_tier"]), "high")


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from agent_capsule import Capsule, Destination, HumanApprovalRequired, PolicyViolationError


ROOT = Path(__file__).resolve().parents[2]
CRM_POLICY = ROOT / "fixtures" / "policies" / "crm-policy.json"
RESTRICTIVE_POLICY = ROOT / "fixtures" / "policies" / "restrictive-policy.json"


CRM_DESTINATION = Destination(
    id="crm",
    type="external_tool",
    domain="api.crm.example",
    provider="Example CRM",
    risk="high",
)


MODEL_DESTINATION = Destination(
    id="model_provider",
    type="model_provider",
    domain="api.model.example",
    provider="Example Model",
    risk="medium",
)


class GuardModeTests(unittest.TestCase):
    def test_guard_mode_fails_closed_when_policy_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PolicyViolationError):
                Capsule.init(mode="guard", policy="missing-policy.json", trace_dir=tmp)

    def test_guard_blocks_undeclared_high_risk_egress_before_call(self):
        called = False
        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(mode="guard", policy=str(RESTRICTIVE_POLICY), trace_dir=tmp)

            def update_crm(payload):
                nonlocal called
                called = True
                return {"ok": True}

            guarded_tool = capsule.wrap_tool(
                update_crm,
                component_name="crm.update_account",
                destination=fresh_destination("crm_shadow", risk="high"),
            )

            with self.assertRaises(PolicyViolationError) as raised:
                with capsule.run("guard-block-run"):
                    guarded_tool({
                        "email": "claimant@example.com",
                        "account_notes": "Claim requires review because medical context is present",
                    })

            self.assertFalse(called)
            self.assertNotIn("claimant@example.com", str(raised.exception))
            trace = load_only_trace(tmp)
            span = next(item for item in trace["spans"] if item["component_name"] == "crm.update_account")
            self.assertEqual(span["status"], "blocked")
            self.assertEqual(span["policy_decision"]["action"], "block")
            self.assertEqual(span["policy_decision"]["reason"], "undeclared high-risk egress")
            serialized = json.dumps(trace, sort_keys=True)
            self.assertNotIn("claimant@example.com", serialized)
            self.assertNotIn("Claim requires review because medical context is present", serialized)

    def test_guard_redacts_before_supported_tool_call(self):
        received = {}
        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(mode="guard", policy=str(CRM_POLICY), trace_dir=tmp)

            def update_crm(payload):
                received.update(payload)
                return {"status": "queued"}

            guarded_tool = capsule.wrap_tool(
                update_crm,
                component_name="crm.update_account",
                destination=fresh_destination("crm", risk="high"),
            )

            with capsule.run("guard-redact-run"):
                guarded_tool({
                    "account_id": "acct-123",
                    "email": "claimant@example.com",
                    "account_notes": "Claim requires review because medical context is present",
                })

            self.assertEqual(received["account_id"], "acct-123")
            self.assertEqual(received["email"], "[redacted:email]")
            self.assertEqual(received["account_notes"], "[redacted:account_notes]")
            trace = load_only_trace(tmp)
            span = next(item for item in trace["spans"] if item["component_name"] == "crm.update_account")
            self.assertEqual(span["status"], "redacted")
            self.assertEqual(span["policy_decision"]["action"], "redact")
            self.assertEqual(span["policy_decision"]["fields"], ["account_notes", "email"])

    def test_guard_warns_and_allows_configured_warning(self):
        called = False
        policy = {
            "version": 1,
            "agent": {"name": "claims-triage", "owner": "platform-team"},
            "destinations": {},
            "defaults": {
                "undeclared_high_risk_egress": "block",
                "undeclared_destination": "warn",
                "secrets": "block",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            policy_path = Path(tmp) / "warn-policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            capsule = Capsule.init(mode="guard", policy=str(policy_path), trace_dir=tmp)

            def low_risk_tool(payload):
                nonlocal called
                called = True
                return {"ok": True}

            guarded_tool = capsule.wrap_tool(
                low_risk_tool,
                component_name="support.enrich",
                destination=fresh_destination("support_tool", risk="low"),
            )

            with capsule.run("guard-warn-run"):
                guarded_tool({"support_tier": "gold"})

            self.assertTrue(called)
            self.assertTrue(capsule.warnings)
            trace = load_only_trace(tmp)
            span = next(item for item in trace["spans"] if item["component_name"] == "support.enrich")
            self.assertEqual(span["status"], "ok")
            self.assertEqual(span["policy_decision"]["action"], "warn")

    def test_guard_allows_only_selected_fields_before_call(self):
        received = {}
        policy = {
            "version": 1,
            "agent": {"name": "claims-triage", "owner": "platform-team"},
            "destinations": {
                "crm": {
                    "type": "external_tool",
                    "domain": "api.crm.example",
                    "risk": "high",
                    "allowed_data": ["account_id"],
                    "redact": [],
                    "require_approval": [],
                }
            },
            "defaults": {
                "undeclared_high_risk_egress": "block",
                "undeclared_destination": "warn",
                "secrets": "block",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            policy_path = Path(tmp) / "allow-fields-policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            capsule = Capsule.init(mode="guard", policy=str(policy_path), trace_dir=tmp)

            def update_crm(payload):
                received.update(payload)
                return {"ok": True}

            guarded_tool = capsule.wrap_tool(
                update_crm,
                component_name="crm.update_account",
                destination=fresh_destination("crm", risk="high"),
            )

            with capsule.run("guard-allow-fields-run"):
                guarded_tool({
                    "account_id": "acct-123",
                    "email": "claimant@example.com",
                    "account_notes": "Claim requires review because medical context is present",
                })

            self.assertEqual(received, {"account_id": "acct-123"})
            trace = load_only_trace(tmp)
            span = next(item for item in trace["spans"] if item["component_name"] == "crm.update_account")
            self.assertEqual(span["status"], "ok")
            self.assertEqual(span["policy_decision"]["action"], "allow_fields")
            self.assertEqual(span["policy_decision"]["fields"], ["account_id"])

    def test_guard_requires_human_approval_without_handler(self):
        called = False
        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(mode="guard", policy=str(CRM_POLICY), trace_dir=tmp)

            def classify_claim(payload):
                nonlocal called
                called = True
                return "approved"

            guarded_model = capsule.wrap_model_client(
                classify_claim,
                component_name="classify-claim",
                destination=fresh_destination("model_provider", risk="medium"),
            )

            with self.assertRaises(HumanApprovalRequired) as raised:
                with capsule.run("guard-approval-run"):
                    guarded_model({"medical_information": "Neck pain reported after accident"})

            self.assertFalse(called)
            self.assertNotIn("Neck pain reported after accident", str(raised.exception))
            trace = load_only_trace(tmp)
            span = next(item for item in trace["spans"] if item["component_name"] == "classify-claim")
            self.assertEqual(span["status"], "approval_required")
            self.assertEqual(span["policy_decision"]["action"], "require_approval")

    def test_guard_approval_handler_receives_safe_request_and_allows(self):
        requests = []
        called = False

        def approve(request):
            requests.append(request)
            return True

        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(
                mode="guard",
                policy=str(CRM_POLICY),
                trace_dir=tmp,
                approval_handler=approve,
            )

            def classify_claim(payload):
                nonlocal called
                called = True
                return "approved"

            guarded_model = capsule.wrap_model_client(
                classify_claim,
                component_name="classify-claim",
                destination=fresh_destination("model_provider", risk="medium"),
            )

            with capsule.run("guard-approved-run"):
                guarded_model({"medical_information": "Neck pain reported after accident"})

            self.assertTrue(called)
            self.assertEqual(len(requests), 1)
            request = requests[0]
            self.assertEqual(request["decision_action"], "require_approval")
            self.assertEqual(request["fields"], ["medical_information"])
            self.assertTrue(request["content_hash"].startswith("sha256:"))
            self.assertNotIn("Neck pain reported after accident", json.dumps(request, sort_keys=True))
            trace = load_only_trace(tmp)
            span = next(item for item in trace["spans"] if item["component_name"] == "classify-claim")
            self.assertEqual(span["status"], "ok")
            self.assertEqual(span["policy_decision"]["action"], "require_approval")


def fresh_destination(destination_id: str, risk: str) -> Destination:
    return Destination(
        id=destination_id,
        type="external_tool" if destination_id != "model_provider" else "model_provider",
        domain="api.%s.example" % destination_id.replace("_", "-"),
        provider="Example",
        risk=risk,
    )


def load_only_trace(root: str) -> dict:
    trace_path = next((Path(root) / "metadata").glob("*.json"))
    return json.loads(trace_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

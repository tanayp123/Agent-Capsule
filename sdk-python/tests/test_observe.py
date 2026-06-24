import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from agent_capsule import Capsule, Destination, classified_field


ROOT = Path(__file__).resolve().parents[2]
CRM_POLICY = ROOT / "fixtures" / "policies" / "crm-policy.json"

MODEL_DESTINATION = Destination(
    id="model_provider",
    type="model_provider",
    domain="api.model.example",
    provider="Example Model",
    risk="medium",
    declared_in_policy=False,
)

CRM_DESTINATION = Destination(
    id="crm",
    type="external_tool",
    domain="api.crm.example",
    provider="Example CRM",
    risk="high",
    declared_in_policy=False,
)


@dataclasses.dataclass
class Claim:
    policy_number: str
    email: str = dataclasses.field(metadata={"agent_capsule_data_classes": ["email"]})
    incident_description: str = ""


class FakePydanticField:
    def __init__(self, data_classes):
        self.json_schema_extra = {"agent_capsule_data_classes": data_classes}


class FakePydanticPayload:
    model_fields = {
        "account_notes": FakePydanticField(["account_notes"]),
    }

    def __init__(self):
        self.account_notes = "customer asked for escalation"

    def model_dump(self):
        return {"account_notes": self.account_notes}


class ObserveModeTests(unittest.TestCase):
    def test_successful_run_writes_schema_compatible_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(
                mode="observe",
                policy="missing-policy.json",
                trace_dir=tmp,
                agent_name="claims-triage",
            )

            def classify_claim(claim):
                return "approved"

            wrapped_model = capsule.wrap_model_client(
                classify_claim,
                component_name="classify-claim",
                destination=MODEL_DESTINATION,
            )

            with capsule.run("claim-triage") as run:
                claim = Claim(
                    policy_number="POL-123",
                    email="person@example.com",
                    incident_description="minor collision",
                )
                result = wrapped_model(claim)
                run.record_output(result)

            traces = list((Path(tmp) / "metadata").glob("*.json"))
            self.assertEqual(len(traces), 1)
            trace = json.loads(traces[0].read_text(encoding="utf-8"))
            self.assertEqual(trace["agent"]["name"], "claims-triage")
            self.assertEqual(trace["mode"], "observe")
            self.assertEqual(trace["language"], "python")
            self.assertGreaterEqual(len(trace["spans"]), 3)
            self.assertTrue(capsule.warnings)

            model_span = next(span for span in trace["spans"] if span["component_type"] == "model_call")
            self.assertEqual(model_span["destination_id"], "model_provider")
            self.assertIn("email", model_span["data_classes"])
            self.assertIn("policy_number", model_span["data_classes"])
            self.assertTrue(model_span["content_hash"].startswith("sha256:"))
            self.assertNotIn("person@example.com", traces[0].read_text(encoding="utf-8"))

    def test_error_span_records_summary_and_reraises(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(mode="observe", trace_dir=tmp)

            def failing_tool():
                raise RuntimeError("tool unavailable")

            wrapped_tool = capsule.wrap_tool(
                failing_tool,
                component_name="crm.upsert_account",
                destination=CRM_DESTINATION,
            )

            with self.assertRaises(RuntimeError):
                with capsule.run("failure-run"):
                    wrapped_tool()

            trace_path = next((Path(tmp) / "metadata").glob("*.json"))
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            error_spans = [span for span in trace["spans"] if span["status"] == "error"]
            self.assertTrue(error_spans)
            self.assertEqual(error_spans[0]["error_summary"]["type"], "RuntimeError")
            self.assertTrue(error_spans[0]["error_summary"]["stack_hash"].startswith("sha256:"))

    def test_nested_spans_preserve_parent_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(mode="observe", trace_dir=tmp)

            with capsule.run("nested-run") as run:
                with run.span("retrieval_call", "fetch-policy", payload={"policy_number": "POL-7"}) as outer:
                    with run.span("database_call", "policy-db", payload={"account_id": "A-1"}) as inner:
                        self.assertNotEqual(outer.span_id, inner.span_id)

            trace = json.loads(next((Path(tmp) / "metadata").glob("*.json")).read_text(encoding="utf-8"))
            retrieval = next(span for span in trace["spans"] if span["component_name"] == "fetch-policy")
            database = next(span for span in trace["spans"] if span["component_name"] == "policy-db")
            self.assertEqual(database["parent_span_id"], retrieval["span_id"])

    def test_pydantic_like_field_metadata_is_classified(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(mode="observe", trace_dir=tmp)

            with capsule.run("pydantic-run") as run:
                with run.span("tool_call", "crm.notes", payload=FakePydanticPayload(), destination=CRM_DESTINATION):
                    pass

            trace = json.loads(next((Path(tmp) / "metadata").glob("*.json")).read_text(encoding="utf-8"))
            span = next(item for item in trace["spans"] if item["component_name"] == "crm.notes")
            self.assertIn("account_notes", span["data_classes"])

    def test_classified_field_helper(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(mode="observe", trace_dir=tmp)

            with capsule.run("classified-field-run") as run:
                with run.span(
                    "tool_call",
                    "custom-tool",
                    payload={"custom": classified_field("value", ["medical_information"])},
                    destination=CRM_DESTINATION,
                ):
                    pass

            trace = json.loads(next((Path(tmp) / "metadata").glob("*.json")).read_text(encoding="utf-8"))
            span = next(item for item in trace["spans"] if item["component_name"] == "custom-tool")
            self.assertIn("medical_information", span["data_classes"])

    def test_loaded_policy_records_redaction_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(mode="observe", policy=str(CRM_POLICY), trace_dir=tmp)
            crm_destination = Destination(
                id="crm",
                type="external_tool",
                domain="api.crm.example",
                provider="Example CRM",
                risk="high",
                declared_in_policy=False,
            )

            with capsule.run("policy-run") as run:
                with run.span(
                    "tool_call",
                    "crm.update_account",
                    payload={
                        "email": "person@example.com",
                        "account_notes": "customer asked for escalation",
                    },
                    destination=crm_destination,
                ):
                    pass

            trace = json.loads(next((Path(tmp) / "metadata").glob("*.json")).read_text(encoding="utf-8"))
            span = next(item for item in trace["spans"] if item["component_name"] == "crm.update_account")
            self.assertEqual(span["status"], "redacted")
            self.assertEqual(span["policy_decision"]["action"], "redact")
            self.assertEqual(span["policy_decision"]["fields"], ["account_notes", "email"])
            destination = next(item for item in trace["destinations"] if item["id"] == "crm")
            self.assertTrue(destination["declared_in_policy"])
            self.assertEqual(destination["allowed_data_classes"], ["account_id", "support_tier"])


class AsyncObserveModeTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_model_wrapper_preserves_run_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(mode="observe", trace_dir=tmp)

            async def async_model(payload):
                return "async approved"

            wrapped_model = capsule.wrap_model_client(
                async_model,
                component_name="async-classify-claim",
                destination=MODEL_DESTINATION,
            )

            async with capsule.run("async-run") as run:
                async with run.span("retrieval_call", "async-fetch-policy", payload={"policy_number": "POL-8"}):
                    await wrapped_model({"prompt": "classify claim"})

            trace = json.loads(next((Path(tmp) / "metadata").glob("*.json")).read_text(encoding="utf-8"))
            retrieval = next(span for span in trace["spans"] if span["component_name"] == "async-fetch-policy")
            model = next(span for span in trace["spans"] if span["component_name"] == "async-classify-claim")
            self.assertEqual(model["parent_span_id"], retrieval["span_id"])
            self.assertIn("prompt_content", model["data_classes"])


if __name__ == "__main__":
    unittest.main()

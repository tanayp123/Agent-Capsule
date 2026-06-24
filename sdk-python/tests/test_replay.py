import copy
import json
import tempfile
import unittest
from pathlib import Path

from agent_capsule import Capsule, Destination, compare_trace_to_replay, replay_trace_from_store, scan_safe_trace
from agent_capsule.replay import ReplayError


MODEL_DESTINATION = Destination(
    id="model_provider",
    type="model_provider",
    domain="api.model.example",
    provider="Example Model",
    risk="medium",
)

CRM_DESTINATION = Destination(
    id="crm",
    type="external_tool",
    domain="api.crm.example",
    provider="Example CRM",
    risk="high",
)


class ReplayTests(unittest.TestCase):
    def test_structural_replay_preserves_shape_without_plaintext(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule, run, raw_values = _write_sample_run(tmp)

            replay = replay_trace_from_store(capsule.trace_store, run.run_id, created_at="2026-06-23T18:00:00Z")
            serialized = json.dumps(replay, sort_keys=True)
            trace = capsule.trace_store.read_trace(run.trace_id)
            comparison = compare_trace_to_replay(trace, replay)

            self.assertEqual(replay["mode"], "structural")
            self.assertFalse(replay["payload_policy"]["raw_payloads_exported"])
            self.assertEqual(comparison["status"], "match")
            self.assertTrue(replay["spans"])
            self.assertFalse(scan_safe_trace(replay, raw_values))
            for raw_value in raw_values:
                self.assertNotIn(raw_value, serialized)

    def test_mocked_replay_emits_model_and_tool_mocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule, run, raw_values = _write_sample_run(tmp)

            replay = replay_trace_from_store(capsule.trace_store, run.run_id, mode="mocked")
            actions = {span["replay_action"] for span in replay["spans"]}
            self.assertIn("mocked_model_response", actions)
            self.assertIn("mocked_tool_result", actions)
            mocked_spans = [span for span in replay["spans"] if "mocked_result" in span]
            self.assertTrue(mocked_spans)
            self.assertFalse(scan_safe_trace(replay, raw_values))

    def test_redacted_replay_uses_redacted_payload_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule, run, raw_values = _write_sample_run(tmp)

            replay = replay_trace_from_store(capsule.trace_store, run.run_id, mode="redacted")
            redacted_spans = [span for span in replay["spans"] if span.get("redacted_payloads")]
            self.assertTrue(redacted_spans)
            replacements = {
                payload["replacement"]
                for span in redacted_spans
                for payload in span["redacted_payloads"]
            }
            self.assertIn("[redacted:input]", replacements)
            self.assertFalse(scan_safe_trace(replay, raw_values))

    def test_approved_plaintext_replay_requires_explicit_flag_and_exports_no_plaintext(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule, run, raw_values = _write_sample_run(tmp)

            with self.assertRaises(ReplayError):
                replay_trace_from_store(capsule.trace_store, run.run_id, mode="approved_plaintext")

            replay = replay_trace_from_store(
                capsule.trace_store,
                run.run_id,
                mode="approved_plaintext",
                approve_plaintext=True,
            )
            self.assertTrue(replay["payload_policy"]["encrypted_payloads_decrypted"])
            self.assertGreater(replay["payload_policy"]["plaintext_payloads_used"], 0)
            self.assertFalse(scan_safe_trace(replay, raw_values))
            serialized = json.dumps(replay, sort_keys=True)
            for raw_value in raw_values:
                self.assertNotIn(raw_value, serialized)

    def test_comparison_detects_structure_timing_token_policy_and_error_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule, run, _raw_values = _write_sample_run(tmp)
            trace = capsule.trace_store.read_trace(run.trace_id)
            replay = replay_trace_from_store(capsule.trace_store, run.run_id)
            changed = copy.deepcopy(replay)

            model_span = next(span for span in changed["spans"] if span["component_type"] == "model_call")
            model_span["component_name"] = "different-model"
            model_span["simulated_duration_ms"] += 100
            model_span["token_count"] = 999
            model_span["policy_decision_action"] = "block"
            model_span["status"] = "error"
            model_span["error_type"] = "RuntimeError"
            changed["destinations"].append({
                "id": "new_destination",
                "type": "external_tool",
                "domain": "api.new.example",
                "risk": "high",
                "declared_in_policy": False,
                "observed_data_classes": ["email"],
            })

            comparison = compare_trace_to_replay(trace, changed)
            categories = {item["category"] for item in comparison["differences"]}
            self.assertEqual(comparison["status"], "diverged")
            self.assertIn("span_structure", categories)
            self.assertIn("timing", categories)
            self.assertIn("token_counts", categories)
            self.assertIn("policy_decision_changes", categories)
            self.assertIn("error_changes", categories)
            self.assertIn("destination_changes", categories)


def _write_sample_run(trace_dir):
    capsule = Capsule.init(mode="observe", trace_dir=trace_dir, agent_name="claims-triage")
    raw_values = [
        "person@example.com",
        "Claim requires review because medical context is present",
        "approved with review",
    ]

    def classify_claim(payload):
        return raw_values[2]

    def update_crm(payload):
        return {"status": "queued"}

    model = capsule.wrap_model_client(
        classify_claim,
        component_name="classify-claim",
        destination=MODEL_DESTINATION,
        token_counter=lambda result: len(result.split()),
    )
    tool = capsule.wrap_tool(
        update_crm,
        component_name="crm.update_account",
        destination=CRM_DESTINATION,
    )

    with capsule.run("replay-run") as run:
        result = model({"prompt": "classify", "email": raw_values[0]})
        tool({"email": raw_values[0], "account_notes": raw_values[1]})
        run.record_output(result)

    self_check_trace_path = next((Path(trace_dir) / "metadata").glob("*.json"))
    assert self_check_trace_path.exists()
    return capsule, run, raw_values


if __name__ == "__main__":
    unittest.main()

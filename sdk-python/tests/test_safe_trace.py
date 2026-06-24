import json
import tempfile
import unittest

from agent_capsule import Capsule, Destination, export_safe_trace_from_store, scan_safe_trace
from agent_capsule.safe_trace import SafeTraceError, build_safe_trace


CRM_DESTINATION = Destination(
    id="crm",
    type="external_tool",
    domain="api.crm.example",
    provider="Example CRM",
    risk="high",
)


class SafeTraceTests(unittest.TestCase):
    def test_safe_trace_export_keeps_diagnostics_without_payload_plaintext(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(mode="observe", trace_dir=tmp, agent_name="claims-triage")
            raw_values = [
                "person@example.com",
                "Neck pain reported after accident",
                "Claim requires review because medical context is present",
            ]

            with capsule.run("safe-export-run") as run:
                with run.span(
                    "tool_call",
                    "crm.update_account",
                    payload={
                        "email": raw_values[0],
                        "medical_information": raw_values[1],
                        "account_notes": raw_values[2],
                    },
                    destination=CRM_DESTINATION,
                ):
                    pass

            safe_trace = export_safe_trace_from_store(capsule.trace_store, run.run_id)
            serialized = json.dumps(safe_trace, sort_keys=True)
            self.assertEqual(safe_trace["source_trace_id"], run.trace_id)
            self.assertEqual(safe_trace["redaction_profile"], "team_debug")
            self.assertTrue(safe_trace["workflow_graph"]["nodes"])
            self.assertTrue(safe_trace["content_hashes"])
            self.assertIn("hashed:email", safe_trace["redaction_markers"])
            self.assertFalse(scan_safe_trace(safe_trace, raw_values))
            for raw_value in raw_values:
                self.assertNotIn(raw_value, serialized)

    def test_error_messages_are_sanitized_before_export(self):
        trace = {
            "trace_id": "trc_error_001",
            "run_id": "run_error_001",
            "agent": {"name": "claims-triage", "version": "0.1.0"},
            "language": "python",
            "runtime_version": "3.10.14",
            "sdk_version": "0.1.0",
            "spans": [
                {
                    "span_id": "spn_error",
                    "parent_span_id": None,
                    "component_type": "tool_call",
                    "component_name": "crm.update_account",
                    "start_time": "2026-06-23T18:00:00Z",
                    "end_time": "2026-06-23T18:00:01Z",
                    "status": "error",
                    "payload_size_bytes": 128,
                    "token_count": None,
                    "content_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "data_classes": ["email"],
                    "destination_id": "crm",
                    "policy_decision": {
                        "action": "warn",
                        "reason": "observe_only: undeclared high-risk egress",
                        "policy_version": 1,
                        "fields": ["email"],
                    },
                    "error_summary": {
                        "type": "RuntimeError",
                        "message": "failed for person@example.com with token sk-123456789abc",
                        "stack_hash": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    },
                    "redaction_markers": ["hashed:email"],
                }
            ],
        }

        safe_trace = build_safe_trace(trace)
        serialized = json.dumps(safe_trace, sort_keys=True)
        self.assertNotIn("person@example.com", serialized)
        self.assertNotIn("sk-123456789abc", serialized)
        self.assertIn("[redacted]", safe_trace["spans"][0]["error_summary"])
        self.assertFalse(scan_safe_trace(safe_trace))

    def test_scanner_rejects_sensitive_keys_and_values(self):
        unsafe_trace = {
            "safe_trace_version": 1,
            "source_trace_id": "trc_unsafe_001",
            "created_at": "2026-06-23T18:00:00Z",
            "created_by": "developer@example.com",
            "payload": "secret value",
        }

        findings = scan_safe_trace(unsafe_trace)
        self.assertTrue(any("reserved sensitive key payload" in finding for finding in findings))
        self.assertTrue(any("sensitive-looking plaintext" in finding for finding in findings))

    def test_created_by_email_is_replaced(self):
        trace = {
            "trace_id": "trc_created_by_001",
            "run_id": "run_created_by_001",
            "agent": {"version": "0.1.0"},
            "language": "python",
            "runtime_version": "3.10.14",
            "sdk_version": "0.1.0",
            "spans": [
                {
                    "span_id": "spn_root",
                    "component_type": "workflow",
                    "component_name": "root",
                    "start_time": "2026-06-23T18:00:00Z",
                    "end_time": "2026-06-23T18:00:00Z",
                    "status": "ok",
                    "payload_size_bytes": 0,
                    "token_count": None,
                    "content_hash": None,
                    "policy_decision": {"action": "not_evaluated", "reason": "workflow span"},
                    "error_summary": None,
                    "redaction_markers": [],
                }
            ],
        }

        safe_trace = build_safe_trace(trace, created_by="developer@example.com")
        self.assertEqual(safe_trace["created_by"], "local-developer")
        self.assertFalse(scan_safe_trace(safe_trace))

    def test_export_missing_run_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule = Capsule.init(mode="observe", trace_dir=tmp)
            with self.assertRaises(SafeTraceError):
                export_safe_trace_from_store(capsule.trace_store, "run_missing")


if __name__ == "__main__":
    unittest.main()

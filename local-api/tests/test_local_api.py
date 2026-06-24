import json
import hashlib
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from agent_capsule import Capsule, Destination
from agent_capsule_local_api import LocalApiConfig, run_server


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "fixtures" / "manifests" / "signed-manifest.json"
RAW_VALUES = [
    "claimant@example.com",
    "Neck pain reported after accident",
    "Claim requires review because medical context is present",
]


class LocalApiTests(unittest.TestCase):
    def test_auth_cors_and_safe_metadata_endpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = create_trace_workspace(Path(tmp))
            server, thread = start_server(
                trace_dir=paths["trace_dir"],
                token="session-token",
                policy_path=paths["policy_path"],
                manifest_path=MANIFEST,
                allowed_console_origin="http://127.0.0.1:3018",
            )
            try:
                status, unauthorized, _headers = request_json(server, "GET", "/health")
                self.assertEqual(status, 401)
                self.assertFalse(unauthorized["ok"])

                status, health, headers = request_json(
                    server,
                    "GET",
                    "/health",
                    token="session-token",
                    origin="http://127.0.0.1:3018",
                )
                self.assertEqual(status, 200)
                self.assertTrue(health["ok"])
                self.assertEqual(headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:3018")

                status, _health, headers = request_json(
                    server,
                    "GET",
                    "/health",
                    token="session-token",
                    origin="https://example.com",
                )
                self.assertEqual(status, 200)
                self.assertIsNone(headers.get("Access-Control-Allow-Origin"))

                run_id = paths["run_id"]
                endpoints = [
                    ("GET", "/runs", None),
                    ("GET", f"/runs/{run_id}", None),
                    ("GET", f"/runs/{run_id}/timeline", None),
                    ("GET", f"/runs/{run_id}/data-flow", None),
                    ("GET", f"/runs/{run_id}/privacy-map", None),
                    ("GET", f"/runs/{run_id}/policy-decisions", None),
                    ("POST", f"/runs/{run_id}/export-safe-trace", {"redaction_profile": "team_debug"}),
                    ("POST", f"/runs/{run_id}/replay", {"mode": "structural"}),
                    ("GET", "/manifests/claims-triage", None),
                ]
                responses = []
                for method, path, body in endpoints:
                    status, payload, _headers = request_json(
                        server,
                        method,
                        path,
                        token="session-token",
                        body=body,
                    )
                    self.assertEqual(status, 200, path)
                    responses.append(payload)

                serialized = json.dumps(responses, sort_keys=True)
                for raw_value in RAW_VALUES:
                    self.assertNotIn(raw_value, serialized)
                self.assertIn("undeclared_high_risk_egress", serialized)
                self.assertNotIn("sig_test_value", serialized)
            finally:
                stop_server(server, thread)

    def test_payload_reveal_is_disabled_by_default_and_audited(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = create_trace_workspace(Path(tmp))
            audit_path = Path(tmp) / "audit.log"
            payload_id = first_payload_id(paths["trace_dir"], paths["trace_id"])
            server, thread = start_server(
                trace_dir=paths["trace_dir"],
                token="session-token",
                audit_path=audit_path,
            )
            try:
                status, payload, _headers = request_json(
                    server,
                    "POST",
                    f"/payloads/{payload_id}",
                    token="session-token",
                    body={"trace_id": paths["trace_id"]},
                )
                self.assertEqual(status, 404)
                self.assertFalse(payload["ok"])

                status, payload, _headers = request_json(
                    server,
                    "POST",
                    f"/payloads/{payload_id}/reveal-local",
                    token="session-token",
                    body={"trace_id": paths["trace_id"]},
                )
                self.assertEqual(status, 403)
                self.assertFalse(payload["ok"])
                self.assertNotIn("claimant@example.com", json.dumps(payload))
            finally:
                stop_server(server, thread)

            audit = audit_path.read_text(encoding="utf-8")
            self.assertIn("payload_reveal_attempt", audit)
            self.assertIn('"allowed": false', audit)
            self.assertNotIn("claimant@example.com", audit)

    def test_payload_reveal_requires_explicit_server_enablement(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = create_trace_workspace(Path(tmp))
            audit_path = Path(tmp) / "audit-enabled.log"
            payload_id = first_payload_id(paths["trace_dir"], paths["trace_id"])
            server, thread = start_server(
                trace_dir=paths["trace_dir"],
                token="session-token",
                audit_path=audit_path,
                reveal_enabled=True,
            )
            try:
                status, payload, _headers = request_json(
                    server,
                    "POST",
                    f"/payloads/{payload_id}/reveal-local",
                    token="session-token",
                    body={"trace_id": paths["trace_id"]},
                )
                self.assertEqual(status, 200)
                self.assertTrue(payload["ok"])
                self.assertIn("claimant@example.com", json.dumps(payload))
            finally:
                stop_server(server, thread)

            audit = audit_path.read_text(encoding="utf-8")
            self.assertIn("payload_reveal_attempt", audit)
            self.assertIn("payload_revealed", audit)
            self.assertNotIn("claimant@example.com", audit)

    def test_live_agent_test_creates_encrypted_trace_and_safe_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = create_trace_workspace(Path(tmp))
            audit_path = Path(tmp) / "audit-live.log"
            server, thread = start_server(
                trace_dir=paths["trace_dir"],
                token="session-token",
                policy_path=paths["policy_path"],
                audit_path=audit_path,
            )
            try:
                status, payload, _headers = request_json(
                    server,
                    "POST",
                    "/live-agents/claims-triage/run",
                    token="session-token",
                    body={"scenario_id": "sensitive-crm-egress"},
                )
                self.assertEqual(status, 200)
                self.assertTrue(payload["ok"])
                self.assertTrue(payload["run"]["run_id"].startswith("run_live_claims_triage_"))
                self.assertEqual(payload["test_scenario"]["id"], "sensitive-crm-egress")
                self.assertEqual(payload["test_result"]["status"], "needs_review")
                self.assertTrue(payload["test_result"]["safe_payloads_only"])
                self.assertEqual(payload["safe_trace"]["source_trace_id"], payload["run"]["trace_id"])
                self.assertGreaterEqual(payload["proof"]["policy_findings"], 1)
                self.assertTrue(payload["proof"]["safe_trace_ready"])
                self.assertIn("crm_tool", json.dumps(payload["privacy_map"]))

                serialized = json.dumps(payload, sort_keys=True)
                for raw_value in RAW_VALUES:
                    self.assertNotIn(raw_value, serialized)
                self.assertIn("hashed:email", serialized)

                index_path = paths["trace_dir"] / "payload-index" / ("%s.json" % payload["run"]["trace_id"])
                self.assertTrue(index_path.exists())
                self.assertGreater(len(json.loads(index_path.read_text(encoding="utf-8"))), 0)

                status, suite, _headers = request_json(
                    server,
                    "POST",
                    "/live-agents/claims-triage/scenario-suite",
                    token="session-token",
                    body={},
                )
                self.assertEqual(status, 200)
                self.assertTrue(suite["ok"])
                self.assertEqual(suite["scenario_count"], 3)
                self.assertEqual(suite["overall_status"], "needs_review")
                self.assertTrue(suite["safe_payloads_only"])
                self.assertEqual(
                    [result["scenario_id"] for result in suite["results"]],
                    ["sensitive-crm-egress", "metadata-only-check", "approval-required"],
                )
                self.assertTrue(all(result["run_id"].startswith("run_live_claims_triage_") for result in suite["results"]))
                serialized_suite = json.dumps(suite, sort_keys=True)
                for raw_value in RAW_VALUES:
                    self.assertNotIn(raw_value, serialized_suite)

                status, evidence, _headers = request_json(
                    server,
                    "POST",
                    "%s/evidence-package" % ("/runs/%s" % payload["run"]["run_id"]),
                    token="session-token",
                    body={
                        "policy_response": {
                            "action": "require_approval",
                            "title": "Require human approval",
                            "outcome": "Human approval is required before CRM update.",
                            "ci_status": "CI gate: passes with approval control recorded.",
                            "patch_preview": [
                                "crm_tool:",
                                "  require_approval: [email, account_notes]",
                            ],
                        }
                    },
                )
                self.assertEqual(status, 200)
                self.assertTrue(evidence["ok"])
                self.assertTrue(evidence["package_id"].startswith("evidence_run_live_claims_triage_"))
                self.assertEqual(evidence["selected_policy_response"]["action"], "require_approval")
                self.assertEqual(evidence["contents"]["safe_trace"]["source_trace_id"], payload["run"]["trace_id"])
                self.assertEqual(evidence["contents"]["privacy_map"]["run_id"], payload["run"]["run_id"])
                self.assertFalse(evidence["redaction_attestation"]["contains_plaintext_payloads"])
                self.assertTrue(evidence["ci_gate"]["blocks_plaintext_payloads"])
                self.assertTrue(evidence["artifact"]["saved"])
                self.assertTrue(evidence["artifact"]["relative_path"].startswith(".agent-capsule/evidence/"))
                self.assertEqual(evidence["artifact"]["verification_status"], "verified")
                self.assertTrue(evidence["artifact"]["sha256"].startswith("sha256:"))

                serialized_evidence = json.dumps(evidence, sort_keys=True)
                for raw_value in RAW_VALUES:
                    self.assertNotIn(raw_value, serialized_evidence)

                artifact_path = paths["trace_dir"].parent / "evidence" / evidence["download_filename"]
                self.assertTrue(artifact_path.exists())
                saved_artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
                self.assertEqual(saved_artifact["package_id"], evidence["package_id"])
                saved_hash = "sha256:%s" % hashlib.sha256(artifact_path.read_bytes()).hexdigest()
                self.assertEqual(saved_hash, evidence["artifact"]["sha256"])
                sidecar_path = artifact_path.with_suffix(artifact_path.suffix + ".sha256")
                self.assertTrue(sidecar_path.exists())
                self.assertIn(saved_hash, sidecar_path.read_text(encoding="utf-8"))
                saved_serialized = json.dumps(saved_artifact, sort_keys=True)
                for raw_value in RAW_VALUES:
                    self.assertNotIn(raw_value, saved_serialized)

                status, verification, _headers = request_json(
                    server,
                    "GET",
                    "/evidence-packages/%s/verify" % evidence["package_id"],
                    token="session-token",
                )
                self.assertEqual(status, 200)
                self.assertEqual(verification["verification_status"], "verified")
                self.assertEqual(verification["sha256"], saved_hash)

                status, customer_report, _headers = request_json(
                    server,
                    "GET",
                    "/evidence-packages/%s/customer-report" % evidence["package_id"],
                    token="session-token",
                )
                self.assertEqual(status, 200)
                self.assertTrue(customer_report["ok"])
                self.assertEqual(customer_report["verification"]["status"], "verified")
                self.assertEqual(customer_report["customer_summary"]["status"], "ready")
                self.assertGreaterEqual(customer_report["scorecard"]["score"], 90)
                self.assertEqual(customer_report["scorecard"]["status"], "ready")
                self.assertIn("destination_control", [
                    check["id"] for check in customer_report["scorecard"]["checks"]
                ])
                self.assertFalse(customer_report["privacy_summary"]["plaintext_payloads_included"])
                self.assertGreaterEqual(customer_report["privacy_summary"]["destination_count"], 1)
                self.assertGreaterEqual(customer_report["privacy_summary"]["finding_count"], 1)
                self.assertIn("crm_tool", json.dumps(customer_report))
                serialized_report = json.dumps(customer_report, sort_keys=True)
                for raw_value in RAW_VALUES:
                    self.assertNotIn(raw_value, serialized_report)

                artifact_path.write_text(artifact_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
                status, tampered, _headers = request_json(
                    server,
                    "GET",
                    "/evidence-packages/%s/verify" % evidence["package_id"],
                    token="session-token",
                )
                self.assertEqual(status, 200)
                self.assertEqual(tampered["verification_status"], "mismatch")

                status, runs, _headers = request_json(
                    server,
                    "GET",
                    "/runs",
                    token="session-token",
                )
                self.assertEqual(status, 200)
                self.assertIn(payload["run"]["run_id"], [run["run_id"] for run in runs["runs"]])
            finally:
                stop_server(server, thread)

            audit = audit_path.read_text(encoding="utf-8")
            self.assertIn("live_agent_test_captured", audit)
            self.assertIn("sensitive-crm-egress", audit)
            self.assertIn("scenario_suite_captured", audit)
            self.assertIn("evidence_package_created", audit)
            self.assertIn("evidence_package_verified", audit)
            self.assertIn("customer_verification_report_created", audit)
            for raw_value in RAW_VALUES:
                self.assertNotIn(raw_value, audit)

    def test_session_end_stops_non_keep_alive_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = create_trace_workspace(Path(tmp))
            server, thread = start_server(trace_dir=paths["trace_dir"], token="session-token")
            status, payload, _headers = request_json(
                server,
                "POST",
                "/session/end",
                token="session-token",
            )
            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
            server.server_close()


def create_trace_workspace(root: Path) -> Dict[str, Any]:
    trace_dir = root / ".agent-capsule" / "traces"
    policy_path = root / "agent-capsule.policy.json"
    policy_path.write_text(json.dumps({
        "version": 1,
        "agent": {"name": "claims-triage", "owner": "platform-team"},
        "destinations": {
            "model_vendor": {
                "type": "model_provider",
                "domain": "models.example.com",
                "risk": "medium",
                "allowed_data": ["email", "account_notes", "model_output"],
                "redact": [],
                "require_approval": [],
            }
        },
        "defaults": {
            "undeclared_high_risk_egress": "block",
            "undeclared_destination": "warn",
            "secrets": "block",
        },
    }, indent=2), encoding="utf-8")

    capsule = Capsule.init(
        mode="observe",
        policy=str(policy_path),
        trace_dir=str(trace_dir),
        agent_name="claims-triage",
        agent_version="0.1.0",
    )
    model_destination = Destination(
        id="model_vendor",
        type="model_provider",
        domain="models.example.com",
        provider="Example Models",
        risk="medium",
    )
    crm_destination = Destination(
        id="crm_tool",
        type="external_tool",
        domain="crm.example.com",
        provider="Example CRM",
        risk="high",
    )
    with capsule.run("triage", run_id="run_local_api_001") as run:
        with run.span(
            "model_call",
            "coverage-review-model",
            payload={
                "email": "claimant@example.com",
                "account_notes": "Neck pain reported after accident",
            },
            destination=model_destination,
            token_count=7,
        ):
            pass
        with run.span(
            "tool_call",
            "crm-update",
            payload={
                "email": "claimant@example.com",
                "account_notes": "Neck pain reported after accident",
            },
            destination=crm_destination,
        ):
            pass
        run.record_output("Claim requires review because medical context is present")
    return {
        "trace_dir": trace_dir,
        "policy_path": policy_path,
        "run_id": run.run_id,
        "trace_id": run.trace_id,
    }


def first_payload_id(trace_dir: Path, trace_id: str) -> str:
    records = json.loads((trace_dir / "payload-index" / f"{trace_id}.json").read_text(encoding="utf-8"))
    return records[0]["payload_id"]


def start_server(
    trace_dir: Path,
    token: str,
    policy_path: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
    audit_path: Optional[Path] = None,
    reveal_enabled: bool = False,
    allowed_console_origin: Optional[str] = None,
) -> Tuple[Any, threading.Thread]:
    server = run_server(LocalApiConfig(
        trace_dir=trace_dir,
        session_token=token,
        port=0,
        policy_path=policy_path,
        manifest_path=manifest_path,
        audit_path=audit_path,
        reveal_enabled=reveal_enabled,
        allowed_console_origin=allowed_console_origin,
    ))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def stop_server(server: Any, thread: threading.Thread) -> None:
    server.shutdown()
    thread.join(timeout=3)
    server.server_close()


def request_json(
    server: Any,
    method: str,
    path: str,
    token: Optional[str] = None,
    body: Optional[Dict[str, Any]] = None,
    origin: Optional[str] = None,
) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
    url = "http://127.0.0.1:%s%s" % (server.server_address[1], path)
    data = json.dumps(body or {}).encode("utf-8") if body is not None else None
    headers = {}
    if token:
        headers["Authorization"] = "Bearer %s" % token
    if origin:
        headers["Origin"] = origin
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8")), dict(response.headers)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, json.loads(raw), dict(exc.headers)


if __name__ == "__main__":
    unittest.main()

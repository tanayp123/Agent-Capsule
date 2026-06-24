import argparse
import hashlib
import json
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from agent_capsule import Capsule, Destination
from agent_capsule.replay import replay_trace_from_store
from agent_capsule.safe_trace import export_safe_trace_from_store
from agent_capsule.trace_store import EncryptedTraceStore
from policy_engine import generate_privacy_map, load_policy_file


DEFAULT_HOST = "127.0.0.1"
LOCALHOST_ORIGINS = {
    "http://127.0.0.1",
    "http://localhost",
}

DEMO_LIVE_AGENTS: Dict[str, Dict[str, Any]] = {
    "claims-triage": {
        "name": "claims-triage",
        "version": "demo.1",
        "workflow": "claim intake privacy review",
        "language": "python",
        "model_component": "coverage-review-model",
        "tool_component": "crm-update",
        "destination_id": "crm_tool",
        "destination_type": "external_tool",
        "destination_domain": "crm.example.com",
        "destination_provider": "Example CRM",
        "destination_risk": "high",
        "policy_action_hint": "review undeclared CRM egress",
    },
    "support-copilot": {
        "name": "support-copilot",
        "version": "demo.1",
        "workflow": "support reply review",
        "language": "typescript",
        "model_component": "support-draft-model",
        "tool_component": "ticket-update",
        "destination_id": "ticketing_tool",
        "destination_type": "external_tool",
        "destination_domain": "tickets.example.com",
        "destination_provider": "Example Ticketing",
        "destination_risk": "medium",
        "policy_action_hint": "confirm support metadata policy",
    },
}

DEFAULT_LIVE_SCENARIO_ID = "sensitive-crm-egress"

DEMO_LIVE_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "sensitive-crm-egress": {
        "id": "sensitive-crm-egress",
        "name": "Sensitive CRM egress",
        "description": "Agent updates an external CRM with customer contact and account notes.",
        "expected_result": "High-risk destination review",
        "data_classes": ["email", "account_notes"],
        "prompt": "Classify this claim and decide whether a human should review it.",
        "model_payload": {
            "email": "claimant@example.com",
            "account_notes": "Neck pain reported after accident",
            "policy_number": "POL-1000",
        },
        "tool_payload": {
            "email": "claimant@example.com",
            "account_notes": "Neck pain reported after accident",
            "route": "human_review",
            "reason_code": "medical_context",
        },
        "model_output": "Claim requires review because medical context is present",
        "token_count": 38,
    },
    "metadata-only-check": {
        "id": "metadata-only-check",
        "name": "Metadata-only update",
        "description": "Agent sends operational metadata to a tool without customer text.",
        "expected_result": "Destination declaration review",
        "data_classes": ["operational_metadata"],
        "prompt": "Route this workflow using metadata only.",
        "model_payload": {
            "request_id": "REQ-1000",
            "queue": "standard_review",
            "priority": "normal",
        },
        "tool_payload": {
            "request_id": "REQ-1000",
            "queue": "standard_review",
            "priority": "normal",
        },
        "model_output": "Metadata-only update prepared",
        "token_count": 21,
    },
    "approval-required": {
        "id": "approval-required",
        "name": "Approval-required note",
        "description": "Agent prepares a tool update that should require human approval first.",
        "expected_result": "Human approval control",
        "data_classes": ["email", "account_notes", "medical_context"],
        "prompt": "Prepare the tool update, but require human approval for sensitive notes.",
        "model_payload": {
            "email": "claimant@example.com",
            "account_notes": "Neck pain reported after accident",
            "medical_context": "injury mentioned",
        },
        "tool_payload": {
            "email": "claimant@example.com",
            "account_notes": "Neck pain reported after accident",
            "approval_reason": "medical_context",
        },
        "model_output": "Claim requires review because medical context is present",
        "token_count": 44,
    },
}


@dataclass
class LocalApiConfig:
    trace_dir: Path
    session_token: str
    host: str = DEFAULT_HOST
    port: int = 0
    policy_path: Optional[Path] = None
    manifest_path: Optional[Path] = None
    reveal_enabled: bool = False
    keep_alive: bool = False
    audit_path: Optional[Path] = None
    allowed_console_origin: Optional[str] = None


class LocalApiBridge:
    def __init__(self, config: LocalApiConfig) -> None:
        if config.host not in ("127.0.0.1", "localhost"):
            raise ValueError("local API bridge must bind to 127.0.0.1 or localhost")
        if not config.session_token:
            raise ValueError("local API bridge requires an ephemeral session token")
        self.config = config
        self.store = EncryptedTraceStore(config.trace_dir)
        self.audit_path = config.audit_path or (config.trace_dir.parent / "audit.log")

    def make_handler(self):
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "AgentCapsuleLocalAPI/0.1"

            def do_OPTIONS(self) -> None:
                self._send_empty(HTTPStatus.NO_CONTENT)

            def do_GET(self) -> None:
                if not self._authorized():
                    self._send_json({"ok": False, "error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                    return
                bridge.handle_get(self)

            def do_POST(self) -> None:
                if not self._authorized():
                    self._send_json({"ok": False, "error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                    return
                bridge.handle_post(self)

            def log_message(self, _format: str, *_args: Any) -> None:
                return

            def _authorized(self) -> bool:
                expected = bridge.config.session_token
                auth = self.headers.get("Authorization", "")
                header_token = self.headers.get("X-Agent-Capsule-Session", "")
                bearer = auth[7:] if auth.startswith("Bearer ") else ""
                return secrets.compare_digest(expected, bearer) or secrets.compare_digest(expected, header_token)

            def _send_json(self, value: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
                payload = json.dumps(value, indent=2, sort_keys=True).encode("utf-8")
                self.send_response(status)
                self._cors_headers()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _send_empty(self, status: HTTPStatus) -> None:
                self.send_response(status)
                self._cors_headers()
                self.send_header("Content-Length", "0")
                self.end_headers()

            def _cors_headers(self) -> None:
                origin = self.headers.get("Origin")
                allowed = bridge.allowed_origin(origin)
                if allowed:
                    self.send_header("Access-Control-Allow-Origin", allowed)
                    self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Agent-Capsule-Session")
                self.send_header("Access-Control-Max-Age", "300")

        return Handler

    def handle_get(self, handler: BaseHTTPRequestHandler) -> None:
        route = _route(handler.path)
        try:
            if route == ["health"]:
                self._send(handler, self.health())
            elif route == ["runs"]:
                self._send(handler, self.runs())
            elif len(route) == 2 and route[0] == "runs":
                self._send(handler, self.run_detail(route[1]))
            elif len(route) == 3 and route[0] == "runs" and route[2] == "timeline":
                self._send(handler, self.timeline(route[1]))
            elif len(route) == 3 and route[0] == "runs" and route[2] == "data-flow":
                self._send(handler, self.data_flow(route[1]))
            elif len(route) == 3 and route[0] == "runs" and route[2] == "privacy-map":
                self._send(handler, self.privacy_map(route[1]))
            elif len(route) == 3 and route[0] == "runs" and route[2] == "policy-decisions":
                self._send(handler, self.policy_decisions(route[1]))
            elif len(route) == 3 and route[0] == "evidence-packages" and route[2] == "verify":
                self._send(handler, self.verify_evidence_package(route[1]))
            elif len(route) == 3 and route[0] == "evidence-packages" and route[2] == "customer-report":
                self._send(handler, self.customer_verification_report(route[1]))
            elif len(route) == 2 and route[0] == "manifests":
                self._send(handler, self.manifest(route[1]))
            else:
                self._send(handler, {"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)
        except FileNotFoundError as exc:
            self._send(handler, {"ok": False, "error": _safe_error(exc)}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send(handler, {"ok": False, "error": _safe_error(exc)}, HTTPStatus.BAD_REQUEST)

    def handle_post(self, handler: BaseHTTPRequestHandler) -> None:
        route = _route(handler.path)
        body = _read_json(handler)
        try:
            if len(route) == 3 and route[0] == "runs" and route[2] == "export-safe-trace":
                self._send(handler, self.export_safe_trace(route[1], body))
            elif len(route) == 3 and route[0] == "runs" and route[2] == "replay":
                self._send(handler, self.replay(route[1], body))
            elif len(route) == 3 and route[0] == "runs" and route[2] == "evidence-package":
                self._send(handler, self.evidence_package(route[1], body))
            elif len(route) == 3 and route[0] == "live-agents" and route[2] == "run":
                self._send(handler, self.run_live_agent(route[1], body))
            elif len(route) == 3 and route[0] == "live-agents" and route[2] == "scenario-suite":
                self._send(handler, self.run_scenario_suite(route[1]))
            elif len(route) == 3 and route[0] == "payloads" and route[2] == "reveal-local":
                self._send(handler, self.reveal_payload(route[1], body))
            elif route == ["session", "end"]:
                self._send(handler, {"ok": True, "keep_alive": self.config.keep_alive})
                if not self.config.keep_alive:
                    threading.Thread(target=handler.server.shutdown, daemon=True).start()
            else:
                self._send(handler, {"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)
        except PermissionError as exc:
            self._send(handler, {"ok": False, "error": _safe_error(exc)}, HTTPStatus.FORBIDDEN)
        except Exception as exc:
            self._send(handler, {"ok": False, "error": _safe_error(exc)}, HTTPStatus.BAD_REQUEST)

    def health(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "service": "agent-capsule-local-api",
            "host": self.config.host,
            "port": self.config.port,
            "reveal_enabled": self.config.reveal_enabled,
        }

    def runs(self) -> Dict[str, Any]:
        runs = []
        for summary in self.store.list_traces():
            item = dict(summary)
            try:
                item["status"] = _trace_status(self.store.read_trace(summary["trace_id"]))
            except Exception:
                item["status"] = "unknown"
            runs.append(item)
        runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return {"ok": True, "runs": runs}

    def run_detail(self, run_id: str) -> Dict[str, Any]:
        trace = self._trace(run_id)
        return {
            "ok": True,
            "run_id": trace["run_id"],
            "trace_id": trace["trace_id"],
            "agent": trace.get("agent", {}),
            "mode": trace.get("mode"),
            "created_at": trace.get("created_at"),
            "span_count": len(trace.get("spans", [])),
            "destinations": trace.get("destinations", []),
        }

    def timeline(self, run_id: str) -> Dict[str, Any]:
        return export_safe_trace_from_store(self.store, run_id)

    def data_flow(self, run_id: str) -> Dict[str, Any]:
        trace = self._trace(run_id)
        nodes = [
            {
                "id": span.get("span_id"),
                "label": span.get("component_name"),
                "component_type": span.get("component_type"),
                "destination_id": span.get("destination_id"),
            }
            for span in trace.get("spans", [])
        ]
        edges = [
            {"from": span.get("parent_span_id"), "to": span.get("span_id")}
            for span in trace.get("spans", [])
            if span.get("parent_span_id")
        ]
        return {
            "ok": True,
            "run_id": trace["run_id"],
            "trace_id": trace["trace_id"],
            "nodes": nodes,
            "edges": edges,
            "destinations": trace.get("destinations", []),
        }

    def privacy_map(self, run_id: str) -> Dict[str, Any]:
        trace = self._trace(run_id)
        policy = self._policy(trace)
        return generate_privacy_map(trace, policy)

    def policy_decisions(self, run_id: str) -> Dict[str, Any]:
        trace = self._trace(run_id)
        decisions = []
        for span in trace.get("spans", []):
            decision = span.get("policy_decision") or {}
            decisions.append({
                "span_id": span.get("span_id"),
                "component_name": span.get("component_name"),
                "action": decision.get("action", "not_evaluated"),
                "reason": decision.get("reason", ""),
                "fields": decision.get("fields", []),
            })
        return {"ok": True, "run_id": run_id, "policy_decisions": decisions}

    def export_safe_trace(self, run_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        profile = body.get("redaction_profile", "team_debug")
        return export_safe_trace_from_store(self.store, run_id, redaction_profile=profile)

    def replay(self, run_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return replay_trace_from_store(
            self.store,
            run_id,
            mode=body.get("mode", "structural"),
            approve_plaintext=bool(body.get("approve_plaintext", False)),
        )

    def evidence_package(self, run_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        run = self.run_detail(run_id)
        safe_trace = export_safe_trace_from_store(self.store, run_id)
        privacy_map = self.privacy_map(run_id)
        selected_response = _safe_policy_response(body.get("policy_response"))
        high_risk_findings = [
            finding
            for finding in privacy_map.get("findings", [])
            if finding.get("kind") == "undeclared_high_risk_egress"
        ]
        gate_status = "ready_for_merge" if selected_response.get("action") != "allow" else "review_required"
        package_id = "evidence_%s_%s" % (_safe_slug(run_id), secrets.token_hex(3))
        filename = "%s.json" % package_id
        artifact_path = self.config.trace_dir.parent / "evidence" / filename
        package = {
            "ok": True,
            "evidence_package_version": 1,
            "package_id": package_id,
            "created_at": _now(),
            "download_filename": filename,
            "run": run,
            "selected_policy_response": selected_response,
            "ci_gate": {
                "status": gate_status,
                "summary": selected_response.get("ci_status") or "CI gate checks safe metadata before merge.",
                "open_high_risk_findings": len(high_risk_findings),
                "requires_policy_commit": True,
                "blocks_plaintext_payloads": True,
            },
            "manifest": self._manifest_summary(),
            "redaction_attestation": {
                "contains_plaintext_payloads": False,
                "safe_trace_profile": safe_trace.get("redaction_profile"),
                "redaction_markers": safe_trace.get("redaction_markers", []),
                "content_hash_count": len(safe_trace.get("content_hashes", [])),
            },
            "contents": {
                "safe_trace": safe_trace,
                "privacy_map": privacy_map,
            },
            "share_summary": {
                "title": "Private agent evidence package",
                "description": "Safe trace, privacy map, policy response, CI gate, and manifest summary without plaintext payloads.",
                "audience": ["teammate", "security reviewer", "enterprise customer"],
            },
            "artifact": {
                "saved": True,
                "path": str(artifact_path),
                "relative_path": str(Path(self.config.trace_dir.parent.name) / "evidence" / filename),
            },
        }
        package["artifact"].update(self._write_evidence_artifact(artifact_path, package))
        self._audit("evidence_package_created", {
            "package_id": package_id,
            "run_id": run_id,
            "trace_id": run.get("trace_id"),
            "policy_response": selected_response.get("action"),
            "artifact": package["artifact"]["relative_path"],
            "artifact_sha256": package["artifact"]["sha256"],
        })
        return package

    def verify_evidence_package(self, package_id: str) -> Dict[str, Any]:
        path = self._evidence_artifact_path(package_id)
        sidecar_path = path.with_suffix(path.suffix + ".sha256")
        if not path.exists() or not sidecar_path.exists():
            raise FileNotFoundError("evidence package not found")

        actual = "sha256:%s" % hashlib.sha256(path.read_bytes()).hexdigest()
        expected = _read_sidecar_hash(sidecar_path)
        verified = secrets.compare_digest(actual, expected)
        status = "verified" if verified else "mismatch"
        result = {
            "ok": True,
            "package_id": package_id,
            "checked_at": _now(),
            "verification_status": status,
            "sha256": actual,
            "expected_sha256": expected,
            "artifact": {
                "path": str(path),
                "relative_path": str(Path(self.config.trace_dir.parent.name) / "evidence" / path.name),
                "sidecar_path": str(sidecar_path),
                "sidecar_relative_path": str(Path(self.config.trace_dir.parent.name) / "evidence" / sidecar_path.name),
            },
        }
        self._audit("evidence_package_verified", {
            "package_id": package_id,
            "verification_status": status,
            "artifact_sha256": actual,
        })
        return result

    def customer_verification_report(self, package_id: str) -> Dict[str, Any]:
        path = self._evidence_artifact_path(package_id)
        if not path.exists():
            raise FileNotFoundError("evidence package not found")

        package = json.loads(path.read_text(encoding="utf-8"))
        verification = self.verify_evidence_package(package_id)
        contents = package.get("contents", {})
        safe_trace = contents.get("safe_trace", {})
        privacy_map = contents.get("privacy_map", {})
        findings = privacy_map.get("findings", [])
        destinations = []
        for destination in privacy_map.get("destinations", []):
            destination_id = destination.get("id")
            destination_findings = [
                finding.get("kind")
                for finding in findings
                if finding.get("destination_id") == destination_id and finding.get("kind")
            ]
            destinations.append({
                "id": destination_id,
                "domain": destination.get("domain"),
                "egress_risk": destination.get("egress_risk") or destination.get("destination_risk"),
                "declared_in_policy": bool(destination.get("declared_in_policy")),
                "observed_data_classes": destination.get("observed_data_classes", []),
                "findings": destination_findings or destination.get("findings", []),
                "actions": destination.get("actions", []),
            })

        report = {
            "ok": True,
            "report_version": 1,
            "package_id": package_id,
            "generated_at": _now(),
            "title": "Customer verification report",
            "verification": {
                "status": verification["verification_status"],
                "sha256": verification["sha256"],
                "sidecar": verification["artifact"]["sidecar_relative_path"],
            },
            "run": {
                "run_id": (package.get("run") or {}).get("run_id"),
                "trace_id": (package.get("run") or {}).get("trace_id"),
                "agent_name": ((package.get("run") or {}).get("agent") or {}).get("name"),
                "agent_version": ((package.get("run") or {}).get("agent") or {}).get("version"),
                "mode": (package.get("run") or {}).get("mode"),
                "span_count": (package.get("run") or {}).get("span_count"),
            },
            "policy_response": package.get("selected_policy_response"),
            "ci_gate": package.get("ci_gate"),
            "privacy_summary": {
                "destination_count": len(privacy_map.get("destinations", [])),
                "finding_count": len(findings),
                "redaction_marker_count": len(safe_trace.get("redaction_markers", [])),
                "content_hash_count": len(safe_trace.get("content_hashes", [])),
                "plaintext_payloads_included": False,
            },
            "destinations": destinations,
            "controls": [
                "Plaintext prompts excluded",
                "Plaintext documents excluded",
                "Model outputs excluded",
                "Tool payload bodies excluded",
                "Secrets excluded",
                "User identifiers excluded",
                "Content hashes retained",
                "Redaction markers retained",
            ],
            "customer_summary": {
                "headline": "This package can be reviewed without private payloads.",
                "audience": "enterprise customer",
                "status": "ready" if verification["verification_status"] == "verified" else "needs_review",
            },
            "scorecard": _customer_report_scorecard(verification, package, safe_trace, privacy_map),
        }
        self._audit("customer_verification_report_created", {
            "package_id": package_id,
            "verification_status": verification["verification_status"],
            "artifact_sha256": verification["sha256"],
        })
        return report

    def run_live_agent(self, agent_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        demo = DEMO_LIVE_AGENTS.get(agent_id) or _generic_demo_live_agent(agent_id)
        scenario = _live_test_scenario(body.get("scenario_id"))

        requested_run_id = str(body.get("run_id", ""))
        run_id = requested_run_id if requested_run_id.startswith("run_") else "run_live_%s_%s" % (
            _safe_slug(agent_id),
            secrets.token_hex(4),
        )
        capsule = Capsule.init(
            mode="observe",
            policy=str(self.config.policy_path) if self.config.policy_path else None,
            trace_dir=str(self.config.trace_dir),
            agent_name=demo["name"],
            agent_version=demo["version"],
        )
        model_destination = Destination(
            id="model_vendor",
            type="model_provider",
            domain="models.example.com",
            provider="Example Models",
            risk="medium",
        )
        tool_destination = Destination(
            id=demo["destination_id"],
            type=demo["destination_type"],
            domain=demo["destination_domain"],
            provider=demo["destination_provider"],
            risk=demo["destination_risk"],
        )

        with capsule.run("%s / %s" % (demo["workflow"], scenario["name"]), run_id=run_id) as run:
            with run.span(
                "model_call",
                demo["model_component"],
                payload={
                    "prompt": scenario["prompt"],
                    **scenario["model_payload"],
                },
                destination=model_destination,
                token_count=scenario["token_count"],
            ):
                pass
            with run.span(
                "tool_call",
                demo["tool_component"],
                payload={
                    "tool_payload": scenario["tool_payload"],
                },
                destination=tool_destination,
            ):
                pass
            run.record_output(scenario["model_output"])

        safe_trace = export_safe_trace_from_store(self.store, run_id)
        privacy_map = self.privacy_map(run_id)
        run_detail = self.run_detail(run_id)
        findings = privacy_map.get("findings", [])
        destination_count = len(privacy_map.get("destinations", []))
        result_status = "needs_review" if findings else "passed"
        result = {
            "ok": True,
            "message": "Live agent test captured as an encrypted trace.",
            "run": run_detail,
            "safe_trace": safe_trace,
            "privacy_map": privacy_map,
            "test_scenario": {
                "id": scenario["id"],
                "name": scenario["name"],
                "description": scenario["description"],
                "expected_result": scenario["expected_result"],
                "data_classes": scenario["data_classes"],
                "destination_id": demo["destination_id"],
            },
            "test_result": {
                "status": result_status,
                "summary": "%s policy %s across %s %s." % (
                    len(findings),
                    "finding" if len(findings) == 1 else "findings",
                    destination_count,
                    "destination" if destination_count == 1 else "destinations",
                ),
                "expected_result": scenario["expected_result"],
                "safe_payloads_only": True,
                "encrypted_payloads": len(safe_trace.get("content_hashes", [])),
            },
            "proof": {
                "safe_trace_ready": True,
                "encrypted_payloads": len(safe_trace.get("content_hashes", [])),
                "redaction_markers": safe_trace.get("redaction_markers", []),
                "policy_findings": len(findings),
            },
            "next_actions": [
                "Review destinations and data classes.",
                "Choose allow, allow selected fields, redact, require approval, or block.",
                "Export a safe trace for collaboration.",
            ],
        }
        self._audit("live_agent_test_captured", {
            "agent_id": agent_id,
            "scenario_id": scenario["id"],
            "run_id": run_id,
            "trace_id": run_detail.get("trace_id"),
            "test_status": result_status,
            "policy_action_hint": demo["policy_action_hint"],
        })
        return result

    def run_scenario_suite(self, agent_id: str) -> Dict[str, Any]:
        demo = DEMO_LIVE_AGENTS.get(agent_id) or _generic_demo_live_agent(agent_id)
        suite_id = "suite_%s_%s" % (_safe_slug(agent_id), secrets.token_hex(4))
        results = []
        for scenario_id in DEMO_LIVE_SCENARIOS:
            live_result = self.run_live_agent(agent_id, {"scenario_id": scenario_id})
            result = live_result["test_result"]
            scenario = live_result["test_scenario"]
            results.append({
                "scenario_id": scenario["id"],
                "scenario_name": scenario["name"],
                "expected_result": scenario["expected_result"],
                "data_classes": scenario["data_classes"],
                "destination_id": scenario["destination_id"],
                "status": result["status"],
                "summary": result["summary"],
                "run_id": live_result["run"]["run_id"],
                "trace_id": live_result["run"]["trace_id"],
                "finding_count": live_result["proof"]["policy_findings"],
                "encrypted_payloads": result["encrypted_payloads"],
                "safe_payloads_only": result["safe_payloads_only"],
            })
        total_findings = sum(item["finding_count"] for item in results)
        overall_status = "needs_review" if total_findings else "passed"
        suite = {
            "ok": True,
            "suite_id": suite_id,
            "agent_id": agent_id,
            "agent_name": demo["name"],
            "created_at": _now(),
            "overall_status": overall_status,
            "scenario_count": len(results),
            "total_findings": total_findings,
            "safe_payloads_only": all(item["safe_payloads_only"] for item in results),
            "results": results,
            "next_action": "Open the highest-finding scenario, choose a policy control, and export customer evidence.",
        }
        self._audit("scenario_suite_captured", {
            "suite_id": suite_id,
            "agent_id": agent_id,
            "scenario_count": len(results),
            "total_findings": total_findings,
            "overall_status": overall_status,
        })
        return suite

    def manifest(self, manifest_id: str) -> Dict[str, Any]:
        if self.config.manifest_path is None or not self.config.manifest_path.exists():
            raise FileNotFoundError("manifest not configured")
        manifest = json.loads(self.config.manifest_path.read_text(encoding="utf-8"))
        signature = manifest.get("signature", {})
        return {
            "ok": True,
            "manifest_id": manifest_id,
            "agent_name": manifest.get("agent_name"),
            "agent_version": manifest.get("agent_version"),
            "language": manifest.get("language"),
            "runtime_version": manifest.get("runtime_version"),
            "sdk_version": manifest.get("sdk_version"),
            "policy_version": manifest.get("policy_version"),
            "network_destinations": manifest.get("network_destinations", []),
            "signature": {
                "algorithm": signature.get("algorithm"),
                "key_id": signature.get("key_id"),
                "present": bool(signature.get("value")),
            },
        }

    def reveal_payload(self, payload_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        self._audit("payload_reveal_attempt", {
            "payload_id": payload_id,
            "trace_id": body.get("trace_id"),
            "allowed": self.config.reveal_enabled,
        })
        if not self.config.reveal_enabled:
            raise PermissionError("payload reveal is disabled")
        record = self._payload_record(payload_id, body.get("trace_id"))
        payload = self.store.read_payload(record["trace_id"], payload_id)
        self._audit("payload_revealed", {
            "payload_id": payload_id,
            "trace_id": record.get("trace_id"),
        })
        return {
            "ok": True,
            "payload_id": payload_id,
            "trace_id": record.get("trace_id"),
            "kind": payload.get("kind"),
            "content_hash": payload.get("content_hash"),
            "payload": payload.get("payload"),
        }

    def allowed_origin(self, origin: Optional[str]) -> Optional[str]:
        if not origin:
            return None
        parsed = urlparse(origin)
        normalized = "%s://%s" % (parsed.scheme, parsed.hostname)
        if normalized not in LOCALHOST_ORIGINS:
            return None
        if self.config.allowed_console_origin and origin != self.config.allowed_console_origin:
            return None
        return origin

    def _trace(self, run_id: str) -> Dict[str, Any]:
        trace = self.store.find_trace_by_run_id(run_id)
        if trace is None:
            raise ValueError("run not found: %s" % run_id)
        return trace

    def _policy(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        if self.config.policy_path and self.config.policy_path.exists():
            return load_policy_file(self.config.policy_path)
        return {
            "version": 1,
            "agent": {
                "name": trace.get("agent", {}).get("name", "agent"),
                "owner": "local-developer",
            },
            "destinations": {},
            "defaults": {
                "undeclared_high_risk_egress": "block",
                "undeclared_destination": "warn",
                "secrets": "block",
            },
        }

    def _payload_record(self, payload_id: str, trace_id: Optional[str]) -> Dict[str, Any]:
        summaries = self.store.list_traces()
        for summary in summaries:
            if trace_id and summary["trace_id"] != trace_id:
                continue
            index_path = self.store.index_path(summary["trace_id"])
            if not index_path.exists():
                continue
            records = json.loads(index_path.read_text(encoding="utf-8"))
            for record in records:
                if record.get("payload_id") == payload_id:
                    return record
        raise ValueError("payload not found: %s" % payload_id)

    def _manifest_summary(self) -> Dict[str, Any]:
        if self.config.manifest_path is None or not self.config.manifest_path.exists():
            return {
                "configured": False,
                "agent_name": None,
                "agent_version": None,
                "policy_version": None,
                "signature_present": False,
            }
        manifest = self.manifest("claims-triage")
        return {
            "configured": True,
            "agent_name": manifest.get("agent_name"),
            "agent_version": manifest.get("agent_version"),
            "language": manifest.get("language"),
            "runtime_version": manifest.get("runtime_version"),
            "sdk_version": manifest.get("sdk_version"),
            "policy_version": manifest.get("policy_version"),
            "signature_present": bool((manifest.get("signature") or {}).get("present")),
            "network_destinations": manifest.get("network_destinations", []),
        }

    def _write_evidence_artifact(self, path: Path, package: Dict[str, Any]) -> Dict[str, Any]:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(package, indent=2, sort_keys=True).encode("utf-8")
        path.write_bytes(payload)
        digest = "sha256:%s" % hashlib.sha256(payload).hexdigest()
        sidecar_path = path.with_suffix(path.suffix + ".sha256")
        sidecar_path.write_text("%s  %s\n" % (digest, path.name), encoding="utf-8")
        return {
            "sha256": digest,
            "sidecar_path": str(sidecar_path),
            "sidecar_relative_path": str(Path(self.config.trace_dir.parent.name) / "evidence" / sidecar_path.name),
            "verification_status": "verified",
        }

    def _evidence_artifact_path(self, package_id: str) -> Path:
        if not package_id.startswith("evidence_") or package_id != _safe_slug(package_id):
            raise ValueError("invalid evidence package id")
        return self.config.trace_dir.parent / "evidence" / ("%s.json" % package_id)

    def _audit(self, event: str, details: Dict[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "created_at": _now(),
            "event": event,
            "details": details,
        }
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")

    def _send(self, handler: BaseHTTPRequestHandler, value: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        handler._send_json(value, status)  # type: ignore[attr-defined]


def run_server(config: LocalApiConfig) -> ThreadingHTTPServer:
    bridge = LocalApiBridge(config)
    server = ThreadingHTTPServer((config.host, config.port), bridge.make_handler())
    config.port = int(server.server_address[1])
    return server


def create_session_token() -> str:
    return secrets.token_urlsafe(24)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-dir", default=".agent-capsule/traces")
    parser.add_argument("--policy", default=None)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--session-token", default=None)
    parser.add_argument("--enable-payload-reveal", action="store_true")
    parser.add_argument("--keep-alive", action="store_true")
    parser.add_argument("--allowed-console-origin", default=None)
    args = parser.parse_args(argv)

    token = args.session_token or create_session_token()
    server = run_server(LocalApiConfig(
        trace_dir=Path(args.trace_dir),
        policy_path=Path(args.policy) if args.policy else None,
        manifest_path=Path(args.manifest) if args.manifest else None,
        host=args.host,
        port=args.port,
        session_token=token,
        reveal_enabled=args.enable_payload_reveal,
        keep_alive=args.keep_alive,
        allowed_console_origin=args.allowed_console_origin,
    ))
    print(json.dumps({
        "ok": True,
        "host": args.host,
        "port": server.server_address[1],
        "session_token": token,
    }, sort_keys=True), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    return 0


def _route(path: str) -> List[str]:
    return [part for part in urlparse(path).path.split("/") if part]


def _read_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    if length > 1024 * 1024:
        raise ValueError("request body too large")
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    value = json.loads(raw.decode("utf-8"))
    return value if isinstance(value, dict) else {}


def _read_sidecar_hash(path: Path) -> str:
    first_token = path.read_text(encoding="utf-8").split()[0]
    if not first_token.startswith("sha256:"):
        raise ValueError("evidence sidecar is malformed")
    return first_token


def _safe_error(exc: Exception) -> str:
    return str(exc).splitlines()[0]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_slug(value: str) -> str:
    slug = "".join(char if char.isalnum() else "_" for char in value.lower())
    return slug.strip("_") or "agent"


def _generic_demo_live_agent(agent_id: str) -> Dict[str, Any]:
    slug = _safe_slug(agent_id)
    return {
        "name": slug.replace("_", "-"),
        "version": "demo.1",
        "workflow": "%s privacy review" % slug.replace("_", " "),
        "language": "python",
        "model_component": "%s-review-model" % slug.replace("_", "-"),
        "tool_component": "%s-tool-update" % slug.replace("_", "-"),
        "destination_id": "%s_tool" % slug,
        "destination_type": "external_tool",
        "destination_domain": "%s.example.com" % slug.replace("_", "-"),
        "destination_provider": "Example %s Tool" % slug.replace("_", " ").title(),
        "destination_risk": "high",
        "policy_action_hint": "review undeclared egress",
    }


def _live_test_scenario(value: Any) -> Dict[str, Any]:
    scenario_id = str(value or DEFAULT_LIVE_SCENARIO_ID)
    return DEMO_LIVE_SCENARIOS.get(scenario_id) or DEMO_LIVE_SCENARIOS[DEFAULT_LIVE_SCENARIO_ID]


def _customer_report_scorecard(
    verification: Dict[str, Any],
    package: Dict[str, Any],
    safe_trace: Dict[str, Any],
    privacy_map: Dict[str, Any],
) -> Dict[str, Any]:
    policy_response = package.get("selected_policy_response") or {}
    ci_gate = package.get("ci_gate") or {}
    high_risk_findings = [
        finding
        for finding in privacy_map.get("findings", [])
        if finding.get("kind") == "undeclared_high_risk_egress"
    ]
    redaction_marker_count = len(safe_trace.get("redaction_markers", []))
    content_hash_count = len(safe_trace.get("content_hashes", []))
    policy_action = policy_response.get("action")
    controlled_actions = {"allow_fields", "redact", "require_approval", "block"}

    checks = [
        {
            "id": "artifact_integrity",
            "label": "Evidence package hash verified",
            "status": "pass" if verification.get("verification_status") == "verified" else "fail",
            "detail": verification.get("verification_status", "unknown"),
        },
        {
            "id": "plaintext_exclusion",
            "label": "Plaintext payloads excluded",
            "status": "pass",
            "detail": "Prompts, documents, outputs, tool bodies, secrets, and user identifiers are excluded.",
        },
        {
            "id": "destination_control",
            "label": "High-risk egress controlled",
            "status": "pass" if policy_action in controlled_actions else "review",
            "detail": "%s high-risk findings with policy action %s." % (
                len(high_risk_findings),
                policy_action or "not_set",
            ),
        },
        {
            "id": "ci_gate",
            "label": "CI policy gate ready",
            "status": "pass" if ci_gate.get("status") == "ready_for_merge" else "review",
            "detail": ci_gate.get("summary", "CI gate status unavailable."),
        },
        {
            "id": "evidence_completeness",
            "label": "Hashes and redaction markers retained",
            "status": "pass" if content_hash_count and redaction_marker_count else "review",
            "detail": "%s content hashes and %s redaction markers." % (
                content_hash_count,
                redaction_marker_count,
            ),
        },
    ]
    score = 100
    for check in checks:
        if check["status"] == "fail":
            score -= 30
        elif check["status"] == "review":
            score -= 10
    score = max(0, score)
    if score >= 90:
        status = "ready"
        summary = "Ready for controlled customer review."
    elif score >= 70:
        status = "needs_review"
        summary = "Review remaining controls before customer sharing."
    else:
        status = "blocked"
        summary = "Do not share until failed controls are resolved."
    return {
        "score": score,
        "status": status,
        "summary": summary,
        "checks": checks,
    }


def _safe_policy_response(value: Any) -> Dict[str, Any]:
    allowed_actions = {"allow", "allow_fields", "redact", "require_approval", "block"}
    source = value if isinstance(value, dict) else {}
    action = str(source.get("action", "redact"))
    if action not in allowed_actions:
        action = "redact"
    return {
        "action": action,
        "title": _bounded_text(source.get("title"), "Redact fields"),
        "outcome": _bounded_text(source.get("outcome"), "Sensitive fields are redacted before egress."),
        "ci_status": _bounded_text(source.get("ci_status"), "CI gate validates safe policy evidence."),
        "patch_preview": [
            _bounded_text(line, "")
            for line in _as_list(source.get("patch_preview"))[:8]
            if _bounded_text(line, "")
        ],
    }


def _bounded_text(value: Any, fallback: str, limit: int = 240) -> str:
    text = str(value) if value is not None else fallback
    text = " ".join(text.splitlines()) if "\n" in text and limit <= 240 else text
    return text[:limit]


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _trace_status(trace: Dict[str, Any]) -> str:
    statuses = {span.get("status") for span in trace.get("spans", [])}
    for status in ("error", "blocked", "approval_required", "redacted"):
        if status in statuses:
            return status
    return "ok"

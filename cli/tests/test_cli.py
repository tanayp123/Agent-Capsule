import contextlib
import io
import json
import os
import tempfile
import unittest
import urllib.parse
import urllib.request
from pathlib import Path

from agent_capsule_cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "examples" / "claims-triage-python" / "claims_triage.py"
MANIFEST = ROOT / "fixtures" / "manifests" / "signed-manifest.json"
CRM_POLICY = ROOT / "fixtures" / "policies" / "crm-policy.json"
RESTRICTIVE_POLICY = ROOT / "fixtures" / "policies" / "restrictive-policy.json"
CRM_REVIEW_TRACE = ROOT / "fixtures" / "traces" / "crm-privacy-review.json"
FAILED_MODEL_TRACE = ROOT / "fixtures" / "traces" / "failed-model-call.json"
TOOL_SENSITIVE_TRACE = ROOT / "fixtures" / "traces" / "tool-call-sensitive-payload.json"


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_init_creates_policy_config_and_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                code, stdout, stderr = self.run_cli(["init"])
                self.assertEqual(code, 0, stderr)
                self.assertIn("Initialized Agent Capsule", stdout)
                self.assertTrue(Path("agent-capsule.policy.yaml").exists())
                self.assertTrue(Path(".agent-capsule/config.json").exists())
                self.assertTrue(Path(".agent-capsule/traces/keys/local.key").exists())

    def test_policy_check_valid_and_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                self.assertEqual(self.run_cli(["init"])[0], 0)
                code, stdout, _stderr = self.run_cli(["policy", "check", "--json"])
                self.assertEqual(code, 0)
                self.assertTrue(json.loads(stdout)["ok"])

                Path("bad-policy.yaml").write_text("version: 1\n", encoding="utf-8")
                code, stdout, _stderr = self.run_cli(["policy", "check", "--policy", "bad-policy.yaml", "--json"])
                self.assertEqual(code, 1)
                self.assertFalse(json.loads(stdout)["ok"])

    def test_run_and_trace_list_do_not_print_raw_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                self.assertEqual(self.run_cli(["init"])[0], 0)
                code, stdout, stderr = self.run_cli([
                    "run",
                    "--mode",
                    "observe",
                    "--",
                    "python3",
                    str(SAMPLE),
                ])
                self.assertEqual(code, 0, stderr)
                self.assertNotIn("claimant@example.com", stdout + stderr)
                self.assertTrue(list(Path(".agent-capsule/traces/metadata").glob("*.json")))

                code, stdout, stderr = self.run_cli(["trace", "list", "--json"])
                self.assertEqual(code, 0, stderr)
                listed = json.loads(stdout)
                self.assertEqual(len(listed["traces"]), 1)
                self.assertNotIn("claimant@example.com", stdout)

    def test_trace_export_safe_writes_shareable_artifact(self):
        raw_values = [
            "claimant@example.com",
            "Neck pain reported after accident",
            "Rear-end collision at low speed",
            "Claim requires review because medical context is present",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                self.assertEqual(self.run_cli(["init"])[0], 0)
                code, _stdout, stderr = self.run_cli([
                    "run",
                    "--mode",
                    "observe",
                    "--",
                    "python3",
                    str(SAMPLE),
                ])
                self.assertEqual(code, 0, stderr)
                code, stdout, stderr = self.run_cli(["trace", "list", "--json"])
                self.assertEqual(code, 0, stderr)
                run_id = json.loads(stdout)["traces"][0]["run_id"]

                code, stdout, stderr = self.run_cli([
                    "trace",
                    "export",
                    "--safe",
                    run_id,
                    "--output",
                    "safe-trace.json",
                    "--json",
                ])
                self.assertEqual(code, 0, stderr)
                self.assertTrue(json.loads(stdout)["ok"])
                safe_trace = json.loads(Path("safe-trace.json").read_text(encoding="utf-8"))
                serialized = json.dumps(safe_trace, sort_keys=True)
                self.assertEqual(safe_trace["redaction_profile"], "team_debug")
                self.assertTrue(safe_trace["workflow_graph"]["nodes"])
                self.assertTrue(safe_trace["content_hashes"])
                for raw_value in raw_values:
                    self.assertNotIn(raw_value, serialized + stdout + stderr)

    def test_trace_replay_writes_safe_artifact_and_comparison(self):
        raw_values = [
            "claimant@example.com",
            "Neck pain reported after accident",
            "Rear-end collision at low speed",
            "Claim requires review because medical context is present",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                self.assertEqual(self.run_cli(["init"])[0], 0)
                code, _stdout, stderr = self.run_cli([
                    "run",
                    "--mode",
                    "observe",
                    "--",
                    "python3",
                    str(SAMPLE),
                ])
                self.assertEqual(code, 0, stderr)
                code, stdout, stderr = self.run_cli(["trace", "list", "--json"])
                self.assertEqual(code, 0, stderr)
                run_id = json.loads(stdout)["traces"][0]["run_id"]

                code, stdout, stderr = self.run_cli([
                    "trace",
                    "replay",
                    run_id,
                    "--mode",
                    "mocked",
                    "--output",
                    "replay.json",
                    "--json",
                ])
                self.assertEqual(code, 0, stderr)
                self.assertTrue(json.loads(stdout)["ok"])
                replay = json.loads(Path("replay.json").read_text(encoding="utf-8"))
                self.assertEqual(replay["mode"], "mocked")
                self.assertFalse(replay["payload_policy"]["raw_payloads_exported"])
                self.assertIn("mocked_model_response", {span["replay_action"] for span in replay["spans"]})

                code, stdout, stderr = self.run_cli([
                    "trace",
                    "replay",
                    run_id,
                    "--compare",
                    "replay.json",
                    "--json",
                ])
                self.assertEqual(code, 0, stderr)
                comparison = json.loads(stdout)
                self.assertEqual(comparison["status"], "match")

                serialized = json.dumps(replay, sort_keys=True) + stdout + stderr
                for raw_value in raw_values:
                    self.assertNotIn(raw_value, serialized)

    def test_approved_plaintext_replay_requires_explicit_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                self.assertEqual(self.run_cli(["init"])[0], 0)
                code, _stdout, stderr = self.run_cli([
                    "run",
                    "--mode",
                    "observe",
                    "--",
                    "python3",
                    str(SAMPLE),
                ])
                self.assertEqual(code, 0, stderr)
                code, stdout, stderr = self.run_cli(["trace", "list", "--json"])
                self.assertEqual(code, 0, stderr)
                run_id = json.loads(stdout)["traces"][0]["run_id"]

                code, stdout, _stderr = self.run_cli([
                    "trace",
                    "replay",
                    run_id,
                    "--mode",
                    "approved_plaintext",
                    "--json",
                ])
                self.assertEqual(code, 1)
                self.assertFalse(json.loads(stdout)["ok"])

                code, stdout, stderr = self.run_cli([
                    "trace",
                    "replay",
                    run_id,
                    "--mode",
                    "approved_plaintext",
                    "--approve-plaintext",
                    "--json",
                ])
                self.assertEqual(code, 0, stderr)
                replay = json.loads(stdout)
                self.assertTrue(replay["payload_policy"]["encrypted_payloads_decrypted"])
                self.assertGreater(replay["payload_policy"]["plaintext_payloads_used"], 0)
                self.assertNotIn("claimant@example.com", stdout)

    def test_manifest_inspect_returns_safe_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                code, stdout, stderr = self.run_cli(["manifest", "inspect", str(MANIFEST), "--json"])
                self.assertEqual(code, 0, stderr)
                output = json.loads(stdout)
                self.assertEqual(output["agent_name"], "claims-triage")
                self.assertTrue(output["signature"]["present"])
                self.assertNotIn("sig_test_value", stdout)

    def test_build_creates_signed_manifest_and_safe_report(self):
        raw_prompt = "Never expose this proprietary prompt template"
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                Path("requirements.txt").write_text("agent-capsule==0.1.0\n", encoding="utf-8")
                Path("prompt.txt").write_text(raw_prompt, encoding="utf-8")
                Path("crm-tool.schema.json").write_text(
                    json.dumps({"type": "object", "properties": {"account_id": {"type": "string"}}}),
                    encoding="utf-8",
                )
                code, stdout, stderr = self.run_cli([
                    "build",
                    "--policy",
                    str(ROOT / "fixtures" / "policies" / "crm-policy.json"),
                    "--output",
                    "capsule-manifest.json",
                    "--build-report",
                    "build-report.json",
                    "--prompt-template",
                    "claim_classification=prompt.txt",
                    "--tool-schema",
                    "crm.upsert_account:1.0.0:crm-tool.schema.json",
                    "--model-provider",
                    "Example Model",
                    "--model",
                    "example-large",
                    "--required-secret",
                    "MODEL_PROVIDER_API_KEY",
                    "--usage-meter",
                    "claim_count:claim",
                    "--signing-key",
                    "test-signing-key",
                    "--key-id",
                    "test-key",
                    "--json",
                ])
                self.assertEqual(code, 0, stderr)
                output = json.loads(stdout)
                self.assertTrue(output["ok"])
                manifest = json.loads(Path("capsule-manifest.json").read_text(encoding="utf-8"))
                report = json.loads(Path("build-report.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["agent_name"], "claims-triage")
                self.assertEqual(manifest["signature"]["algorithm"], "hmac-sha256")
                self.assertEqual(manifest["signature"]["key_id"], "test-key")
                self.assertTrue(manifest["signature"]["value"].startswith("hmac-sha256:"))
                self.assertIn("requirements.txt", manifest["dependency_hashes"])
                self.assertIn("claim_classification", manifest["prompt_template_hashes"])
                self.assertEqual(manifest["tool_definitions"][0]["name"], "crm.upsert_account")
                self.assertEqual(manifest["model_configuration"]["provider"], "Example Model")
                self.assertEqual(manifest["required_secrets"], ["MODEL_PROVIDER_API_KEY"])
                self.assertEqual(report["prompt_template_names"], ["claim_classification"])
                serialized = json.dumps(manifest, sort_keys=True) + json.dumps(report, sort_keys=True) + stdout + stderr
                self.assertNotIn(raw_prompt, serialized)
                self.assertNotIn(manifest["signature"]["value"], stdout)

                code, inspect_stdout, inspect_stderr = self.run_cli([
                    "manifest",
                    "inspect",
                    "capsule-manifest.json",
                    "--json",
                ])
                self.assertEqual(code, 0, inspect_stderr)
                inspected = json.loads(inspect_stdout)
                self.assertTrue(inspected["signature"]["present"])
                self.assertEqual(inspected["prompt_template_hashes"], manifest["prompt_template_hashes"])
                self.assertNotIn(manifest["signature"]["value"], inspect_stdout)
                self.assertNotIn(raw_prompt, inspect_stdout)

    def test_build_is_reproducible_and_dependency_changes_are_detectable(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                Path("requirements.txt").write_text("agent-capsule==0.1.0\n", encoding="utf-8")
                base_args = [
                    "build",
                    "--policy",
                    str(ROOT / "fixtures" / "policies" / "crm-policy.json"),
                    "--signing-key",
                    "test-signing-key",
                    "--key-id",
                    "test-key",
                    "--json",
                ]
                code, stdout, stderr = self.run_cli(base_args + ["--output", "manifest-a.json", "--build-report", "report-a.json"])
                self.assertEqual(code, 0, stderr)
                code, stdout, stderr = self.run_cli(base_args + ["--output", "manifest-b.json", "--build-report", "report-b.json"])
                self.assertEqual(code, 0, stderr)
                manifest_a = json.loads(Path("manifest-a.json").read_text(encoding="utf-8"))
                manifest_b = json.loads(Path("manifest-b.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest_a, manifest_b)

                Path("requirements.txt").write_text("agent-capsule==0.2.0\n", encoding="utf-8")
                code, stdout, stderr = self.run_cli(base_args + ["--output", "manifest-c.json", "--build-report", "report-c.json"])
                self.assertEqual(code, 0, stderr)
                manifest_c = json.loads(Path("manifest-c.json").read_text(encoding="utf-8"))
                self.assertNotEqual(
                    manifest_a["dependency_hashes"]["requirements.txt"],
                    manifest_c["dependency_hashes"]["requirements.txt"],
                )
                self.assertNotEqual(manifest_a["signature"]["value"], manifest_c["signature"]["value"])

    def test_manifest_inspect_rejects_missing_signature_and_malformed_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
                manifest.pop("signature")
                Path("missing-signature.json").write_text(json.dumps(manifest), encoding="utf-8")
                code, stdout, stderr = self.run_cli(["manifest", "inspect", "missing-signature.json", "--json"])
                self.assertEqual(code, 1)
                self.assertFalse(json.loads(stdout)["ok"])
                self.assertIn("signature", stdout)
                self.assertNotIn("sig_test_value", stdout + stderr)

                Path("malformed.json").write_text("{not json", encoding="utf-8")
                code, stdout, stderr = self.run_cli(["manifest", "inspect", "malformed.json", "--json"])
                self.assertEqual(code, 1)
                self.assertFalse(json.loads(stdout)["ok"])
                self.assertNotIn("sig_test_value", stdout + stderr)

    def test_view_returns_local_console_url_with_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                code, stdout, stderr = self.run_cli([
                    "view",
                    "--console-url",
                    "http://127.0.0.1:3018",
                    "--no-open",
                    "--json",
                ])
                self.assertEqual(code, 0, stderr)
                output = json.loads(stdout)
                self.assertTrue(output["ok"])
                self.assertFalse(output["opened"])
                self.assertTrue(output["bridge_started"])
                self.assertIn("127.0.0.1", output["url"])
                self.assertIn("session=", output["url"])
                parsed = urllib.parse.urlparse(output["url"])
                query = urllib.parse.parse_qs(parsed.query)
                session = query["session"][0]
                bridge_url = query["bridge"][0]

                request = urllib.request.Request(
                    "%s/health" % bridge_url,
                    headers={"Authorization": "Bearer %s" % session},
                    method="GET",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    health = json.loads(response.read().decode("utf-8"))
                self.assertTrue(health["ok"])

                shutdown = urllib.request.Request(
                    "%s/session/end" % bridge_url,
                    data=b"{}",
                    headers={
                        "Authorization": "Bearer %s" % session,
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(shutdown, timeout=5) as response:
                    self.assertEqual(response.status, 200)

    def test_json_policy_check_supports_phase1_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                code, stdout, stderr = self.run_cli([
                    "policy",
                    "check",
                    "--policy",
                    str(ROOT / "fixtures" / "policies" / "crm-policy.json"),
                    "--json",
                ])
                self.assertEqual(code, 0, stderr)
                self.assertTrue(json.loads(stdout)["ok"])

    def test_policy_check_fails_on_undeclared_high_risk_egress(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                code, stdout, stderr = self.run_cli([
                    "policy",
                    "check",
                    "--policy",
                    str(RESTRICTIVE_POLICY),
                    "--trace",
                    str(CRM_REVIEW_TRACE),
                    "--fail-on",
                    "high-risk-egress",
                    "--json",
                ])
                self.assertEqual(code, 1, stderr)
                output = json.loads(stdout)
                self.assertFalse(output["ok"])
                self.assertEqual(output["findings"][1]["kind"], "undeclared_high_risk_egress")
                self.assertIn("redact", {item["action"] for item in output["policy_suggestions"]})
                self.assertNotIn("claimant@example.com", stdout)

    def test_policy_check_can_emit_privacy_map_without_failing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                code, stdout, stderr = self.run_cli([
                    "policy",
                    "check",
                    "--policy",
                    str(RESTRICTIVE_POLICY),
                    "--trace",
                    str(CRM_REVIEW_TRACE),
                    "--json",
                ])
                self.assertEqual(code, 0, stderr)
                output = json.loads(stdout)
                self.assertTrue(output["ok"])
                self.assertEqual(output["privacy_maps"][0]["destinations"][0]["id"], "crm")
                self.assertIn("email", output["privacy_maps"][0]["destinations"][0]["observed_data_classes"])

    def test_ci_check_passes_with_declared_policy_trace_and_release_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                code, stdout, stderr = self.run_cli([
                    "ci",
                    "check",
                    "--policy",
                    str(CRM_POLICY),
                    "--trace",
                    str(FAILED_MODEL_TRACE),
                    "--trace",
                    str(TOOL_SENSITIVE_TRACE),
                    "--manifest",
                    str(MANIFEST),
                    "--release",
                    "--json",
                ])
                self.assertEqual(code, 0, stderr)
                output = json.loads(stdout)
                self.assertTrue(output["ok"])
                self.assertEqual(output["summary"]["error_count"], 0)
                self.assertEqual(output["summary"]["trace_count"], 2)
                self.assertNotIn("sig_test_value", stdout)
                self.assertNotIn("claimant@example.com", stdout)

    def test_ci_check_fails_on_privacy_drift_and_missing_release_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                code, stdout, stderr = self.run_cli([
                    "ci",
                    "check",
                    "--policy",
                    str(RESTRICTIVE_POLICY),
                    "--trace",
                    str(CRM_REVIEW_TRACE),
                    "--release",
                    "--json",
                ])
                self.assertEqual(code, 1, stderr)
                output = json.loads(stdout)
                codes = {finding["code"] for finding in output["findings"]}
                self.assertFalse(output["ok"])
                self.assertIn("undeclared_destination", codes)
                self.assertIn("undeclared_high_risk_egress", codes)
                self.assertIn("high_risk_unapproved_destination", codes)
                self.assertIn("manifest_required", codes)
                self.assertTrue(output["annotations"])
                self.assertNotIn("claimant@example.com", stdout)

    def test_ci_check_rejects_malformed_and_old_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                Path("bad-policy.json").write_text("{bad", encoding="utf-8")
                code, stdout, stderr = self.run_cli([
                    "ci",
                    "check",
                    "--policy",
                    "bad-policy.json",
                    "--json",
                ])
                self.assertEqual(code, 1, stderr)
                self.assertIn("policy_malformed", {finding["code"] for finding in json.loads(stdout)["findings"]})

                code, stdout, stderr = self.run_cli([
                    "ci",
                    "check",
                    "--policy",
                    str(CRM_POLICY),
                    "--min-policy-version",
                    "2",
                    "--json",
                ])
                self.assertEqual(code, 1, stderr)
                self.assertIn("policy_version_too_old", {finding["code"] for finding in json.loads(stdout)["findings"]})

    def test_ci_check_rejects_release_manifest_without_signature_or_supported_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
                manifest["runtime_version"] = "3.9.18"
                manifest["signature"]["value"] = ""
                Path("bad-release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                code, stdout, stderr = self.run_cli([
                    "ci",
                    "check",
                    "--policy",
                    str(CRM_POLICY),
                    "--manifest",
                    "bad-release-manifest.json",
                    "--release",
                    "--json",
                ])
                self.assertEqual(code, 1, stderr)
                output = json.loads(stdout)
                codes = {finding["code"] for finding in output["findings"]}
                self.assertIn("manifest_invalid", codes)
                self.assertIn("manifest_signature_missing", codes)
                self.assertIn("runtime_unsupported", codes)
                self.assertNotIn("sig_test_value", stdout)

    def test_demo_create_success_writes_safe_customer_and_vendor_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                manifest_path = self.build_demo_manifest(
                    policy=CRM_POLICY,
                    required_secrets=["MODEL_PROVIDER_API_KEY", "CRM_API_KEY"],
                )
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                signature_value = manifest["signature"]["value"]

                code, stdout, stderr = self.run_cli([
                    "demo",
                    "create",
                    "--customer",
                    "acme-insurance",
                    "--mode",
                    "confidential",
                    "--manifest",
                    str(manifest_path),
                    "--policy",
                    str(CRM_POLICY),
                    "--trace",
                    str(TOOL_SENSITIVE_TRACE),
                    "--secret",
                    "MODEL_PROVIDER_API_KEY",
                    "--secret",
                    "CRM_API_KEY",
                    "--output-dir",
                    "demos",
                    "--json",
                ])
                self.assertEqual(code, 0, stderr)
                output = json.loads(stdout)
                self.assertTrue(output["ok"])
                self.assertTrue(output["attestation"]["verified"])
                self.assertTrue(output["secret_release"]["released"])
                verification = Path(output["verification_page"]).read_text(encoding="utf-8")
                telemetry = json.loads(Path(output["vendor_telemetry"]).read_text(encoding="utf-8"))
                self.assertIn("Agent Capsule Verification", verification)
                self.assertIn("api.crm.example", verification)
                self.assertEqual(telemetry["health"], "ready")
                self.assertEqual(telemetry["trace_summaries"][0]["spans"][0]["policy_decision"]["action"], "redact")
                serialized = stdout + verification + json.dumps(telemetry, sort_keys=True)
                self.assertNotIn(signature_value, serialized)
                self.assertNotIn("claimant@example.com", serialized)
                self.assertNotIn("Sensitive account note", serialized)

    def test_demo_create_fails_closed_on_attestation_failure_and_writes_support_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                manifest_path = self.build_demo_manifest(policy=CRM_POLICY, required_secrets=["MODEL_PROVIDER_API_KEY"])
                Path("failed-attestation.json").write_text(
                    json.dumps({
                        "provider": "local-confidential-like",
                        "status": "failed",
                        "reason": "measurement mismatch",
                    }),
                    encoding="utf-8",
                )
                code, stdout, stderr = self.run_cli([
                    "demo",
                    "create",
                    "--customer",
                    "acme-insurance",
                    "--manifest",
                    str(manifest_path),
                    "--policy",
                    str(CRM_POLICY),
                    "--secret",
                    "MODEL_PROVIDER_API_KEY",
                    "--attestation-evidence",
                    "failed-attestation.json",
                    "--output-dir",
                    "demos",
                    "--json",
                ])
                self.assertEqual(code, 1, stderr)
                output = json.loads(stdout)
                codes = {finding["code"] for finding in output["findings"]}
                self.assertIn("attestation_failed", codes)
                self.assertFalse(output["secret_release"]["released"])
                support_bundle = json.loads(Path(output["support_bundle"]).read_text(encoding="utf-8"))
                self.assertFalse(support_bundle["privacy"]["raw_payloads_included"])
                self.assertFalse(support_bundle["privacy"]["secret_values_included"])

    def test_demo_create_fails_when_required_secrets_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                manifest_path = self.build_demo_manifest(policy=CRM_POLICY, required_secrets=["CRM_API_KEY"])
                code, stdout, stderr = self.run_cli([
                    "demo",
                    "create",
                    "--customer",
                    "acme-insurance",
                    "--manifest",
                    str(manifest_path),
                    "--policy",
                    str(CRM_POLICY),
                    "--output-dir",
                    "demos",
                    "--json",
                ])
                self.assertEqual(code, 1, stderr)
                output = json.loads(stdout)
                self.assertIn("missing_required_secrets", {finding["code"] for finding in output["findings"]})
                self.assertFalse(output["secret_release"]["released"])
                self.assertEqual(output["secret_release"]["missing_secret_names"], ["CRM_API_KEY"])

    def test_demo_create_fails_when_policy_has_undeclared_high_risk_egress(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                manifest_path = self.build_demo_manifest(policy=RESTRICTIVE_POLICY, required_secrets=[])
                code, stdout, stderr = self.run_cli([
                    "demo",
                    "create",
                    "--customer",
                    "acme-insurance",
                    "--manifest",
                    str(manifest_path),
                    "--policy",
                    str(RESTRICTIVE_POLICY),
                    "--trace",
                    str(CRM_REVIEW_TRACE),
                    "--output-dir",
                    "demos",
                    "--json",
                ])
                self.assertEqual(code, 1, stderr)
                output = json.loads(stdout)
                codes = {finding["code"] for finding in output["findings"]}
                self.assertIn("undeclared_high_risk_egress", codes)
                self.assertIsNotNone(output["support_bundle"])
                serialized = stdout + Path(output["support_bundle"]).read_text(encoding="utf-8")
                self.assertNotIn("claimant@example.com", serialized)

    def test_malformed_config_returns_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            with change_dir(tmp):
                Path(".agent-capsule").mkdir()
                Path(".agent-capsule/config.json").write_text("{bad", encoding="utf-8")
                code, stdout, _stderr = self.run_cli(["trace", "list", "--json"])
                self.assertEqual(code, 1)
                output = json.loads(stdout)
                self.assertFalse(output["ok"])
                self.assertIn("malformed Agent Capsule config", output["error"])

    def build_demo_manifest(self, policy, required_secrets):
        Path("requirements.txt").write_text("agent-capsule==0.1.0\n", encoding="utf-8")
        args = [
            "build",
            "--policy",
            str(policy),
            "--output",
            "capsule-manifest.json",
            "--build-report",
            "build-report.json",
            "--model-provider",
            "Example Model",
            "--model",
            "example-large",
            "--runtime-version",
            "3.10.14",
            "--signing-key",
            "demo-test-signing-key",
            "--key-id",
            "demo-test-key",
            "--json",
        ]
        for secret in required_secrets:
            args.extend(["--required-secret", secret])
        code, stdout, stderr = self.run_cli(args)
        self.assertEqual(code, 0, stderr)
        self.assertTrue(json.loads(stdout)["ok"])
        return Path("capsule-manifest.json")


@contextlib.contextmanager
def change_dir(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


if __name__ == "__main__":
    unittest.main()

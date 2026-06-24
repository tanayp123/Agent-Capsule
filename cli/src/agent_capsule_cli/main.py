import argparse
import hashlib
import hmac
import json
import os
import platform
import re
import secrets
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlparse

from agent_capsule import __version__ as SDK_VERSION
from agent_capsule.replay import compare_trace_to_replay, replay_trace_from_store
from agent_capsule.safe_trace import export_safe_trace_from_store
from agent_capsule.trace_store import EncryptedTraceStore
from policy_engine import (
    PolicyEngineError,
    classify_data_risk,
    evaluate_policy,
    generate_privacy_map,
    load_policy_file,
    load_trace_file,
    validate_policy_object as engine_validate_policy_object,
)

DEFAULT_POLICY_PATH = "agent-capsule.policy.yaml"
DEFAULT_CAPSULE_DIR = ".agent-capsule"
DEFAULT_TRACE_DIR = ".agent-capsule/traces"
DEFAULT_MANIFEST_PATH = ".agent-capsule/manifests/capsule-manifest.json"
DEFAULT_BUILD_REPORT_PATH = ".agent-capsule/manifests/build-report.json"
DEFAULT_DEMO_DIR = ".agent-capsule/demos"
MIN_SUPPORTED_POLICY_VERSION = 1
SUPPORTED_DEMO_ENVIRONMENTS = ("local-confidential-like",)
KNOWN_LOCKFILES = (
    "requirements.txt",
    "requirements.lock",
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Cargo.lock",
    "go.sum",
    "pom.xml",
)
HASH_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        if getattr(args, "json", False):
            print_json({"ok": False, "error": safe_error(exc)})
        else:
            print("error: %s" % safe_error(exc), file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capsule",
        description="Private-by-default debugging and policy tooling for AI agents.",
        epilog=(
            "examples:\n"
            "  capsule init\n"
            "  capsule run --mode observe -- python3 agent.py\n"
            "  capsule trace list --json\n"
            "  capsule trace export --safe run_123 --output safe-trace.json\n"
            "  capsule trace replay run_123 --mode structural --output replay.json\n"
            "  capsule view --console-url http://127.0.0.1:3018 --no-open\n"
            "  capsule policy check --trace trace.json --fail-on high-risk-egress\n"
            "  capsule ci check --policy agent-capsule.policy.yaml --trace trace.json --json\n"
            "  capsule demo create --customer acme-insurance --mode confidential\n"
            "  capsule manifest inspect capsule-manifest.json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create local Agent Capsule config")
    add_common_output(init_parser)
    init_parser.add_argument("--force", action="store_true", help="overwrite existing generated files")
    init_parser.set_defaults(handler=handle_init)

    run_parser = subparsers.add_parser("run", help="run an instrumented command")
    add_common_output(run_parser)
    run_parser.add_argument("--mode", default="observe", choices=["observe", "guard", "confidential"])
    run_parser.add_argument("--trace-dir", default=None)
    run_parser.add_argument("--policy", default=None)
    run_parser.add_argument("--show-command-output", action="store_true")
    run_parser.add_argument("command", nargs=argparse.REMAINDER)
    run_parser.set_defaults(handler=handle_run)

    trace_parser = subparsers.add_parser("trace", help="work with local traces")
    trace_subparsers = trace_parser.add_subparsers(dest="trace_command", required=True)
    trace_list_parser = trace_subparsers.add_parser("list", help="list local trace metadata")
    add_common_output(trace_list_parser)
    trace_list_parser.add_argument("--trace-dir", default=None)
    trace_list_parser.set_defaults(handler=handle_trace_list)
    trace_export_parser = trace_subparsers.add_parser("export", help="export safe trace artifacts")
    add_common_output(trace_export_parser)
    trace_export_parser.add_argument("--trace-dir", default=None)
    trace_export_parser.add_argument("--safe", metavar="RUN_ID", help="export a safe trace for this run id")
    trace_export_parser.add_argument("--output", default=None, help="write safe trace JSON to this path")
    trace_export_parser.add_argument(
        "--redaction-profile",
        default="team_debug",
        choices=["strict", "team_debug", "customer_support"],
    )
    trace_export_parser.set_defaults(handler=handle_trace_export)
    trace_replay_parser = trace_subparsers.add_parser("replay", help="replay a local trace safely")
    add_common_output(trace_replay_parser)
    trace_replay_parser.add_argument("run_id")
    trace_replay_parser.add_argument("--trace-dir", default=None)
    trace_replay_parser.add_argument(
        "--mode",
        default="structural",
        choices=["structural", "mocked", "redacted", "approved_plaintext"],
    )
    trace_replay_parser.add_argument("--approve-plaintext", action="store_true")
    trace_replay_parser.add_argument("--output", default=None, help="write replay JSON to this path")
    trace_replay_parser.add_argument("--compare", default=None, help="compare source trace to a replay JSON file")
    trace_replay_parser.set_defaults(handler=handle_trace_replay)

    policy_parser = subparsers.add_parser("policy", help="work with Agent Capsule policies")
    policy_subparsers = policy_parser.add_subparsers(dest="policy_command", required=True)
    policy_check_parser = policy_subparsers.add_parser("check", help="validate policy and trace privacy")
    add_common_output(policy_check_parser)
    policy_check_parser.add_argument("--policy", default=DEFAULT_POLICY_PATH)
    policy_check_parser.add_argument("--trace", action="append", default=[], help="trace metadata JSON to evaluate")
    policy_check_parser.add_argument(
        "--fail-on",
        choices=["high-risk-egress"],
        default=None,
        help="fail when the selected privacy finding is present",
    )
    policy_check_parser.set_defaults(handler=handle_policy_check)

    ci_parser = subparsers.add_parser("ci", help="run Agent Capsule CI gates")
    ci_subparsers = ci_parser.add_subparsers(dest="ci_command", required=True)
    ci_check_parser = ci_subparsers.add_parser("check", help="validate pull request privacy and release evidence")
    add_common_output(ci_check_parser)
    ci_check_parser.add_argument("--policy", default=DEFAULT_POLICY_PATH)
    ci_check_parser.add_argument("--trace", action="append", default=[], help="trace metadata JSON or directory to evaluate")
    ci_check_parser.add_argument("--trace-dir", default=None, help="trace store or metadata directory to evaluate")
    ci_check_parser.add_argument("--manifest", default=None, help="capsule manifest to validate")
    ci_check_parser.add_argument("--release", action="store_true", help="enforce release-build manifest checks")
    ci_check_parser.add_argument("--min-policy-version", type=int, default=MIN_SUPPORTED_POLICY_VERSION)
    ci_check_parser.add_argument(
        "--annotation-format",
        choices=["json", "github", "gitlab", "buildkite"],
        default="json",
        help="label annotations for the target CI system",
    )
    ci_check_parser.set_defaults(handler=handle_ci_check)

    build_capsule_parser = subparsers.add_parser("build", help="create a signed capsule manifest")
    add_common_output(build_capsule_parser)
    build_capsule_parser.add_argument("--source-dir", default=".")
    build_capsule_parser.add_argument("--policy", default=DEFAULT_POLICY_PATH)
    build_capsule_parser.add_argument("--output", default=DEFAULT_MANIFEST_PATH)
    build_capsule_parser.add_argument("--build-report", default=DEFAULT_BUILD_REPORT_PATH)
    build_capsule_parser.add_argument("--agent-name", default=None)
    build_capsule_parser.add_argument("--agent-version", default="0.1.0")
    build_capsule_parser.add_argument("--language", default="python", choices=["python", "typescript", "java", "go", "rust"])
    build_capsule_parser.add_argument("--runtime-version", default=None)
    build_capsule_parser.add_argument("--sdk-version", default=SDK_VERSION)
    build_capsule_parser.add_argument("--container-digest", default=None)
    build_capsule_parser.add_argument("--dependency-lockfile", action="append", default=[])
    build_capsule_parser.add_argument("--prompt-template", action="append", default=[], help="NAME=PATH or PATH")
    build_capsule_parser.add_argument("--tool-schema", action="append", default=[], help="NAME:VERSION:PATH")
    build_capsule_parser.add_argument("--model-provider", default="unspecified")
    build_capsule_parser.add_argument("--model", default="unspecified")
    build_capsule_parser.add_argument("--model-config", default=None)
    build_capsule_parser.add_argument("--required-secret", action="append", default=[])
    build_capsule_parser.add_argument("--usage-meter", action="append", default=[], help="NAME:UNIT")
    build_capsule_parser.add_argument("--signing-key", default=None)
    build_capsule_parser.add_argument("--key-id", default="local-dev")
    build_capsule_parser.set_defaults(handler=handle_build)

    manifest_parser = subparsers.add_parser("manifest", help="work with capsule manifests")
    manifest_subparsers = manifest_parser.add_subparsers(dest="manifest_command", required=True)
    manifest_inspect_parser = manifest_subparsers.add_parser("inspect", help="inspect safe manifest metadata")
    add_common_output(manifest_inspect_parser)
    manifest_inspect_parser.add_argument("manifest", nargs="?")
    manifest_inspect_parser.set_defaults(handler=handle_manifest_inspect)

    demo_parser = subparsers.add_parser("demo", help="create confidential customer demos")
    demo_subparsers = demo_parser.add_subparsers(dest="demo_command", required=True)
    demo_create_parser = demo_subparsers.add_parser("create", help="prepare a private customer proof of concept")
    add_common_output(demo_create_parser)
    demo_create_parser.add_argument("--customer", required=True)
    demo_create_parser.add_argument("--mode", default="confidential", choices=["confidential"])
    demo_create_parser.add_argument("--manifest", default=DEFAULT_MANIFEST_PATH)
    demo_create_parser.add_argument("--policy", default=DEFAULT_POLICY_PATH)
    demo_create_parser.add_argument("--trace", action="append", default=[], help="trace metadata JSON or directory to evaluate")
    demo_create_parser.add_argument("--trace-dir", default=None, help="trace store or metadata directory to evaluate")
    demo_create_parser.add_argument("--output-dir", default=DEFAULT_DEMO_DIR)
    demo_create_parser.add_argument(
        "--environment-provider",
        default="local-confidential-like",
        choices=SUPPORTED_DEMO_ENVIRONMENTS,
    )
    demo_create_parser.add_argument("--attestation-evidence", default=None, help="JSON attestation evidence to capture")
    demo_create_parser.add_argument("--secret-provider", default="manual", choices=["manual", "env", "none"])
    demo_create_parser.add_argument("--secret", action="append", default=[], help="required secret name available for release")
    demo_create_parser.set_defaults(handler=handle_demo_create)

    view_parser = subparsers.add_parser("view", help="open the local Agent Capsule Console")
    add_common_output(view_parser)
    view_parser.add_argument("--console-url", default="http://127.0.0.1:3018")
    view_parser.add_argument("--bridge-url", default=None, help="use an already-running local API bridge")
    view_parser.add_argument("--trace-dir", default=None)
    view_parser.add_argument("--policy", default=None)
    view_parser.add_argument("--manifest", default=None)
    view_parser.add_argument("--port", type=int, default=0, help="local API bridge port; 0 selects an ephemeral port")
    view_parser.add_argument("--session-token", default=None, help="session token for an already-running local bridge")
    view_parser.add_argument("--no-open", action="store_true")
    view_parser.add_argument("--enable-payload-reveal", action="store_true")
    view_parser.add_argument("--keep-alive", action="store_true")
    view_parser.set_defaults(handler=handle_view)

    return parser


def add_common_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")


def handle_init(args: argparse.Namespace) -> int:
    capsule_dir = Path(DEFAULT_CAPSULE_DIR)
    trace_dir = Path(DEFAULT_TRACE_DIR)
    policy_path = Path(DEFAULT_POLICY_PATH)
    config_path = capsule_dir / "config.json"

    capsule_dir.mkdir(exist_ok=True)
    store = EncryptedTraceStore(trace_dir)
    store.ensure_layout()

    if policy_path.exists() and not args.force:
        policy_created = False
    else:
        policy_path.write_text(default_policy_yaml(), encoding="utf-8")
        policy_created = True

    config = {
        "version": 1,
        "trace_dir": DEFAULT_TRACE_DIR,
        "policy_path": DEFAULT_POLICY_PATH,
        "key_path": str(store.key_path),
        "retention_days": 14,
        "remote_sync": False,
    }
    if config_path.exists() and not args.force:
        config_created = False
    else:
        config_path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
        config_created = True

    result = {
        "ok": True,
        "capsule_dir": str(capsule_dir),
        "trace_dir": str(trace_dir),
        "policy_path": str(policy_path),
        "config_path": str(config_path),
        "key_path": str(store.key_path),
        "policy_created": policy_created,
        "config_created": config_created,
    }
    output(args, result, text_lines=[
        "Initialized Agent Capsule.",
        "Policy: %s" % policy_path,
        "Config: %s" % config_path,
        "Trace store: %s" % trace_dir,
    ])
    return 0


def handle_run(args: argparse.Namespace) -> int:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise ValueError("missing command after --")

    config = load_config()
    trace_dir = args.trace_dir or config.get("trace_dir", DEFAULT_TRACE_DIR)
    policy_path = args.policy or config.get("policy_path", DEFAULT_POLICY_PATH)

    env = os.environ.copy()
    env["AGENT_CAPSULE_MODE"] = args.mode
    env["AGENT_CAPSULE_TRACE_DIR"] = trace_dir
    env["AGENT_CAPSULE_POLICY"] = policy_path

    completed = subprocess.run(
        command,
        env=env,
        check=False,
        capture_output=not args.show_command_output,
        text=True,
    )
    result = {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "mode": args.mode,
        "trace_dir": trace_dir,
    }
    if args.json:
        print_json(result)
    elif completed.returncode == 0:
        print("Command completed. Trace metadata is available in %s." % trace_dir)
    else:
        print("Command failed with exit code %s." % completed.returncode, file=sys.stderr)
    return completed.returncode


def handle_trace_list(args: argparse.Namespace) -> int:
    config = load_config()
    trace_dir = args.trace_dir or config.get("trace_dir", DEFAULT_TRACE_DIR)
    store = EncryptedTraceStore(Path(trace_dir))
    traces = store.list_traces()
    result = {"ok": True, "trace_dir": trace_dir, "traces": traces}
    if args.json:
        print_json(result)
    else:
        if not traces:
            print("No traces found in %s." % trace_dir)
        else:
            for trace in traces:
                print(
                    "{trace_id} {run_id} {agent_name} {mode} spans={span_count} created={created_at}".format(
                        **trace
                    )
                )
    return 0


def handle_trace_export(args: argparse.Namespace) -> int:
    if not args.safe:
        result = {"ok": False, "error": "pass --safe <run-id> to export a safe trace"}
        output(args, result, text_lines=[result["error"]])
        return 1

    config = load_config()
    trace_dir = args.trace_dir or config.get("trace_dir", DEFAULT_TRACE_DIR)
    store = EncryptedTraceStore(Path(trace_dir))
    safe_trace = export_safe_trace_from_store(
        store,
        run_id=args.safe,
        redaction_profile=args.redaction_profile,
    )

    output_path = Path(args.output) if args.output else None
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(safe_trace, indent=2, sort_keys=True), encoding="utf-8")
        result = {
            "ok": True,
            "run_id": args.safe,
            "source_trace_id": safe_trace["source_trace_id"],
            "safe_trace": str(output_path),
            "redaction_profile": args.redaction_profile,
        }
        output(args, result, text_lines=["Safe trace exported: %s" % output_path])
        return 0

    print_json(safe_trace)
    return 0


def handle_trace_replay(args: argparse.Namespace) -> int:
    config = load_config()
    trace_dir = args.trace_dir or config.get("trace_dir", DEFAULT_TRACE_DIR)
    store = EncryptedTraceStore(Path(trace_dir))
    replay = replay_trace_from_store(
        store,
        run_id=args.run_id,
        mode=args.mode,
        approve_plaintext=args.approve_plaintext,
    )
    source_trace = store.find_trace_by_run_id(args.run_id)
    if source_trace is None:
        raise ValueError("trace not found for run_id: %s" % args.run_id)

    result = replay
    output_label = "Replay"
    if args.compare:
        comparison_path = Path(args.compare)
        candidate_replay = json.loads(comparison_path.read_text(encoding="utf-8"))
        result = compare_trace_to_replay(source_trace, candidate_replay)
        output_label = "Replay comparison"

    output_path = Path(args.output) if args.output else None
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        summary = {
            "ok": True,
            "run_id": args.run_id,
            "source_trace_id": replay["source_trace_id"],
            "mode": args.mode,
            "output": str(output_path),
        }
        if args.compare:
            summary["comparison_status"] = result["status"]
            summary["difference_count"] = result["summary"]["difference_count"]
        output(args, summary, text_lines=["%s written: %s" % (output_label, output_path)])
        return 0

    if args.json:
        print_json(result)
    elif args.compare:
        print(
            "Replay comparison: {status} differences={count}".format(
                status=result["status"],
                count=result["summary"]["difference_count"],
            )
        )
    else:
        print(
            "Replay prepared: run={run_id} mode={mode} spans={spans} plaintext_used={plaintext}".format(
                run_id=args.run_id,
                mode=args.mode,
                spans=replay["workflow"]["span_count"],
                plaintext=replay["payload_policy"]["plaintext_payloads_used"],
            )
        )
    return 0


def handle_policy_check(args: argparse.Namespace) -> int:
    policy_path = Path(args.policy)
    if not policy_path.exists():
        result = {
            "ok": False,
            "policy": str(policy_path),
            "errors": ["policy file not found"],
        }
        output(args, result, text_lines=["Policy check failed: policy file not found."])
        return 1

    errors = validate_policy_file(policy_path)
    policy = None
    if not errors:
        policy = load_policy_file(policy_path)

    privacy_maps = []
    findings = []
    suggestions = []
    if policy is not None:
        for trace_path_text in args.trace:
            trace_path = Path(trace_path_text)
            if not trace_path.exists():
                errors.append("trace file not found: %s" % trace_path)
                continue
            trace = load_trace_file(trace_path)
            privacy_map = generate_privacy_map(trace, policy)
            privacy_maps.append(privacy_map)
            findings.extend(privacy_map["findings"])
            suggestions.extend(privacy_map["policy_suggestions"])

    failing_findings = []
    if args.fail_on == "high-risk-egress":
        failing_findings = [
            finding
            for finding in findings
            if finding.get("kind") == "undeclared_high_risk_egress"
        ]

    result = {
        "ok": not errors and not failing_findings,
        "policy": str(policy_path),
        "errors": errors,
        "privacy_maps": privacy_maps,
        "findings": findings,
        "policy_suggestions": suggestions,
        "fail_on": args.fail_on,
    }
    if errors:
        output(args, result, text_lines=["Policy check failed: %s" % "; ".join(errors)])
        return 1
    if failing_findings:
        output(
            args,
            result,
            text_lines=[
                "Policy check failed: undeclared high-risk egress remains.",
                _format_findings(failing_findings),
                _format_suggestions(suggestions),
            ],
        )
        return 1

    text_lines = ["Policy check passed: %s" % policy_path]
    if findings:
        text_lines.append(_format_findings(findings))
        if suggestions:
            text_lines.append(_format_suggestions(suggestions))
    output(args, result, text_lines=text_lines)
    return 0


def handle_ci_check(args: argparse.Namespace) -> int:
    policy_path = Path(args.policy)
    trace_paths = collect_ci_trace_paths(args)
    findings: List[Dict[str, Any]] = []
    privacy_maps: List[Dict[str, Any]] = []
    policy = None

    if not policy_path.exists():
        findings.append(ci_finding(
            code="policy_missing",
            message="Policy file was not found.",
            path=policy_path,
        ))
    else:
        policy_errors = validate_policy_file(policy_path)
        if policy_errors:
            for error in policy_errors:
                findings.append(ci_finding(
                    code="policy_malformed",
                    message="Policy file is malformed or invalid: %s" % error,
                    path=policy_path,
                ))
        else:
            policy = load_policy_file(policy_path)
            if policy["version"] < args.min_policy_version:
                findings.append(ci_finding(
                    code="policy_version_too_old",
                    message="Policy version %s is below required version %s." % (
                        policy["version"],
                        args.min_policy_version,
                    ),
                    path=policy_path,
                ))

    if policy is not None:
        for trace_path in trace_paths:
            if not trace_path.exists():
                findings.append(ci_finding(
                    code="trace_missing",
                    message="Trace metadata file was not found.",
                    path=trace_path,
                ))
                continue
            try:
                trace = load_trace_file(trace_path)
            except PolicyEngineError as exc:
                findings.append(ci_finding(
                    code="trace_malformed",
                    message="Trace metadata is malformed: %s" % exc,
                    path=trace_path,
                ))
                continue

            privacy_map = generate_privacy_map(trace, policy)
            privacy_maps.append(privacy_map)
            findings.extend(ci_findings_from_privacy_map(privacy_map, trace_path))
            findings.extend(ci_undeclared_destination_findings(policy, trace, trace_path))
            findings.extend(ci_high_risk_unapproved_findings(policy, trace, trace_path))

    findings.extend(ci_manifest_findings(args))
    findings = dedupe_ci_findings(findings)
    error_count = sum(1 for finding in findings if finding["severity"] == "error")
    warning_count = sum(1 for finding in findings if finding["severity"] == "warning")
    result = {
        "ok": error_count == 0,
        "summary": {
            "error_count": error_count,
            "warning_count": warning_count,
            "trace_count": len(trace_paths),
            "privacy_map_count": len(privacy_maps),
            "release": bool(args.release),
            "annotation_format": args.annotation_format,
        },
        "policy": str(policy_path),
        "traces": [str(path) for path in trace_paths],
        "manifest": args.manifest,
        "findings": findings,
        "annotations": [
            ci_annotation(finding, args.annotation_format)
            for finding in findings
        ],
        "privacy_maps": privacy_maps,
    }

    if result["ok"]:
        output(args, result, text_lines=["Agent Capsule CI check passed."])
        return 0

    output(args, result, text_lines=[
        "Agent Capsule CI check failed.",
        format_ci_findings(findings),
    ])
    return 1


def handle_build(args: argparse.Namespace) -> int:
    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        result = {"ok": False, "error": "source directory not found", "source_dir": str(source_dir)}
        output(args, result, text_lines=["Build failed: source directory not found."])
        return 1

    policy_path = Path(args.policy)
    if not policy_path.exists():
        result = {"ok": False, "error": "policy file not found", "policy": str(policy_path)}
        output(args, result, text_lines=["Build failed: policy file not found."])
        return 1

    policy_errors = validate_policy_file(policy_path)
    if policy_errors:
        result = {"ok": False, "error": "invalid policy", "errors": policy_errors, "policy": str(policy_path)}
        output(args, result, text_lines=["Build failed: %s" % "; ".join(policy_errors)])
        return 1

    policy = load_policy_file(policy_path)
    try:
        manifest = build_capsule_manifest(args, source_dir, policy_path, policy)
    except ValueError as exc:
        result = {"ok": False, "error": safe_error(exc)}
        output(args, result, text_lines=["Build failed: %s" % safe_error(exc)])
        return 1

    validation_errors = validate_manifest_object(manifest)
    if validation_errors:
        result = {"ok": False, "error": "invalid manifest", "errors": validation_errors}
        output(args, result, text_lines=["Build failed: %s" % "; ".join(validation_errors)])
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    build_report = build_manifest_report(manifest, output_path, source_dir)
    report_path = Path(args.build_report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(build_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = {
        "ok": True,
        "manifest": str(output_path),
        "build_report": str(report_path),
        "agent_name": manifest["agent_name"],
        "agent_version": manifest["agent_version"],
        "manifest_hash": build_report["manifest_hash"],
        "signature": {
            "algorithm": manifest["signature"]["algorithm"],
            "key_id": manifest["signature"]["key_id"],
            "present": bool(manifest["signature"]["value"]),
        },
        "dependency_count": len(manifest["dependency_hashes"]),
        "prompt_template_count": len(manifest["prompt_template_hashes"]),
        "tool_count": len(manifest["tool_definitions"]),
    }
    output(args, result, text_lines=[
        "Capsule manifest written: %s" % output_path,
        "Build report written: %s" % report_path,
        "Signature: %s key=%s present" % (
            manifest["signature"]["algorithm"],
            manifest["signature"]["key_id"],
        ),
    ])
    return 0


def handle_manifest_inspect(args: argparse.Namespace) -> int:
    if not args.manifest:
        result = {
            "ok": False,
            "error": "pass a manifest path to inspect safe metadata",
        }
        output(args, result, text_lines=[result["error"]])
        return 1

    path = Path(args.manifest)
    if not path.exists():
        result = {"ok": False, "error": "manifest file not found", "manifest": str(path)}
        output(args, result, text_lines=["Manifest file not found."])
        return 1

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        result = {"ok": False, "error": "manifest JSON is malformed", "manifest": str(path)}
        output(args, result, text_lines=["Manifest inspect failed: manifest JSON is malformed."])
        return 1

    validation_errors = validate_manifest_object(manifest)
    if validation_errors:
        result = {
            "ok": False,
            "error": "invalid manifest",
            "manifest": str(path),
            "errors": validation_errors,
        }
        output(args, result, text_lines=["Manifest inspect failed: %s" % "; ".join(validation_errors)])
        return 1

    safe_fields = {
        "ok": True,
        "manifest": str(path),
        "manifest_hash": hash_file(path),
        "agent_name": manifest.get("agent_name"),
        "agent_version": manifest.get("agent_version"),
        "language": manifest.get("language"),
        "runtime_version": manifest.get("runtime_version"),
        "sdk_version": manifest.get("sdk_version"),
        "container_digest": manifest.get("container_digest"),
        "dependency_hashes": manifest.get("dependency_hashes", {}),
        "prompt_template_hashes": manifest.get("prompt_template_hashes", {}),
        "tool_definitions": manifest.get("tool_definitions", []),
        "model_configuration": manifest.get("model_configuration", {}),
        "policy_hash": manifest.get("policy_hash"),
        "policy_version": manifest.get("policy_version"),
        "network_destinations": manifest.get("network_destinations", []),
        "required_secrets": manifest.get("required_secrets", []),
        "usage_meters": manifest.get("usage_meters", []),
        "signature": {
            "algorithm": manifest.get("signature", {}).get("algorithm"),
            "key_id": manifest.get("signature", {}).get("key_id"),
            "present": bool(manifest.get("signature", {}).get("value")),
        },
    }
    if args.json:
        print_json(safe_fields)
    else:
        print("Agent: %s %s" % (safe_fields["agent_name"], safe_fields["agent_version"]))
        print("Runtime: %s %s" % (safe_fields["language"], safe_fields["runtime_version"]))
        print("Policy version: %s" % safe_fields["policy_version"])
        print("Manifest hash: %s" % safe_fields["manifest_hash"])
        print("Signature: %s key=%s present" % (
            safe_fields["signature"]["algorithm"],
            safe_fields["signature"]["key_id"],
        ))
    return 0


def handle_demo_create(args: argparse.Namespace) -> int:
    customer_id = safe_slug(args.customer)
    demo_dir = Path(args.output_dir) / customer_id
    demo_dir.mkdir(parents=True, exist_ok=True)

    created_at = utc_now()
    findings: List[Dict[str, Any]] = []
    manifest_path = Path(args.manifest)
    policy_path = Path(args.policy)
    trace_paths = collect_ci_trace_paths(args)
    manifest = None
    policy = None

    manifest, manifest_findings = load_demo_manifest(manifest_path)
    findings.extend(manifest_findings)

    if not policy_path.exists():
        findings.append(demo_finding("policy_missing", "Policy file was not found.", policy_path))
    else:
        policy_errors = validate_policy_file(policy_path)
        if policy_errors:
            for error in policy_errors:
                findings.append(demo_finding("policy_malformed", "Policy file is malformed or invalid: %s" % error, policy_path))
        else:
            policy = load_policy_file(policy_path)

    if manifest is not None and policy is not None:
        findings.extend(validate_demo_manifest_policy(manifest, manifest_path, policy, policy_path))
        findings.extend(validate_demo_privacy(policy, trace_paths))

    environment = demo_environment(args, manifest_path, manifest, created_at, preflight_ok=not findings)
    attestation = None
    secret_release = blocked_secret_release(manifest, args.secret_provider, "preflight_failed")

    if not findings:
        attestation = capture_demo_attestation(args, manifest, manifest_path, demo_dir, environment)
        if not attestation.get("verified"):
            findings.append(demo_finding(
                "attestation_failed",
                "Runtime attestation did not verify, so secrets were not released.",
                Path(args.attestation_evidence) if args.attestation_evidence else None,
            ))

    if not findings and attestation is not None:
        secret_release = release_demo_secrets(args, manifest, attestation)
        if secret_release["missing_secret_names"]:
            findings.append(demo_finding(
                "missing_required_secrets",
                "Required secrets are not configured for release.",
                manifest_path,
            ))
        elif not secret_release["released"]:
            findings.append(demo_finding(
                "secret_release_blocked",
                "Secrets were not released because runtime verification was incomplete.",
                manifest_path,
            ))
    elif attestation is None:
        attestation = skipped_demo_attestation(args, manifest_path, demo_dir)

    ok = not findings
    safe_manifest = safe_manifest_summary(manifest, manifest_path) if manifest is not None else {}
    policy_summary = safe_policy_summary(policy, policy_path) if policy is not None else {}
    privacy_summary = demo_privacy_summary(policy, trace_paths) if policy is not None else []

    telemetry = build_vendor_telemetry(
        ok=ok,
        customer=args.customer,
        created_at=created_at,
        manifest=safe_manifest,
        policy=policy_summary,
        environment=environment,
        attestation=attestation,
        secret_release=secret_release,
        trace_paths=trace_paths,
        findings=findings,
    )
    telemetry_path = demo_dir / "vendor-telemetry.json"
    telemetry_path.write_text(json.dumps(telemetry, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    verification_page_path = demo_dir / "customer-verification.html"
    verification_page_path.write_text(
        render_customer_verification_page(
            customer=args.customer,
            ok=ok,
            manifest=safe_manifest,
            policy=policy_summary,
            environment=environment,
            attestation=attestation,
            secret_release=secret_release,
            privacy_summary=privacy_summary,
            findings=findings,
        ),
        encoding="utf-8",
    )

    support_bundle_path = None
    if not ok:
        support_bundle_path = demo_dir / "support-bundle.json"
        support_bundle = build_support_bundle(
            customer=args.customer,
            created_at=created_at,
            manifest=safe_manifest,
            policy=policy_summary,
            environment=environment,
            attestation=attestation,
            secret_release=secret_release,
            findings=findings,
            telemetry_path=telemetry_path,
            verification_page_path=verification_page_path,
        )
        support_bundle_path.write_text(json.dumps(support_bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = {
        "ok": ok,
        "customer": args.customer,
        "mode": args.mode,
        "demo_dir": str(demo_dir),
        "manifest": str(manifest_path),
        "policy": str(policy_path),
        "trace_count": len(trace_paths),
        "verification_page": str(verification_page_path),
        "vendor_telemetry": str(telemetry_path),
        "support_bundle": str(support_bundle_path) if support_bundle_path else None,
        "environment": environment,
        "attestation": {
            "provider": attestation.get("provider"),
            "status": attestation.get("status"),
            "verified": attestation.get("verified"),
            "evidence_hash": attestation.get("evidence_hash"),
        },
        "secret_release": {
            "provider": secret_release["provider"],
            "released": secret_release["released"],
            "required_secret_names": secret_release["required_secret_names"],
            "missing_secret_names": secret_release["missing_secret_names"],
            "receipt_hash": secret_release["receipt_hash"],
        },
        "findings": findings,
    }
    if ok:
        output(args, result, text_lines=[
            "Confidential demo prepared for %s." % args.customer,
            "Verification page: %s" % verification_page_path,
            "Vendor telemetry: %s" % telemetry_path,
        ])
        return 0

    output(args, result, text_lines=[
        "Confidential demo creation failed for %s." % args.customer,
        "Support bundle: %s" % support_bundle_path,
        format_ci_findings(findings),
    ])
    return 1


def handle_view(args: argparse.Namespace) -> int:
    session_token = args.session_token or secrets.token_urlsafe(24)
    bridge_url = args.bridge_url
    bridge_started = False
    bridge_pid = None
    config = load_config()

    if bridge_url is None:
        trace_dir = args.trace_dir or config.get("trace_dir", DEFAULT_TRACE_DIR)
        policy_path = args.policy or config.get("policy_path", DEFAULT_POLICY_PATH)
        bridge_info = start_local_api_bridge(
            trace_dir=trace_dir,
            policy_path=policy_path,
            manifest_path=args.manifest,
            port=args.port,
            session_token=session_token,
            console_url=args.console_url,
            enable_payload_reveal=args.enable_payload_reveal,
            keep_alive=args.keep_alive,
        )
        bridge_url = "http://{host}:{port}".format(host=bridge_info["host"], port=bridge_info["port"])
        bridge_started = True
        bridge_pid = bridge_info.get("pid")

    query = urlencode({
        "bridge": bridge_url,
        "session": session_token,
    })
    separator = "&" if "?" in args.console_url else "?"
    url = "%s%s%s" % (args.console_url.rstrip("/"), separator, query)
    opened = False
    if not args.no_open:
        opened = webbrowser.open(url)

    result = {
        "ok": True,
        "url": url,
        "opened": opened,
        "bridge_url": bridge_url,
        "bridge_started": bridge_started,
        "bridge_pid": bridge_pid,
        "session_token_present": True,
    }
    output(args, result, text_lines=["Console URL: %s" % url])
    return 0


def start_local_api_bridge(
    trace_dir: str,
    policy_path: Optional[str],
    manifest_path: Optional[str],
    port: int,
    session_token: str,
    console_url: str,
    enable_payload_reveal: bool,
    keep_alive: bool,
) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "agent_capsule_local_api",
        "--trace-dir",
        trace_dir,
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--session-token",
        session_token,
        "--allowed-console-origin",
        origin_from_url(console_url),
    ]
    if policy_path:
        cmd.extend(["--policy", policy_path])
    if manifest_path:
        cmd.extend(["--manifest", manifest_path])
    if enable_payload_reveal:
        cmd.append("--enable-payload-reveal")
    if keep_alive:
        cmd.append("--keep-alive")

    env = os.environ.copy()
    env["PYTHONPATH"] = local_api_pythonpath(env.get("PYTHONPATH", ""))
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    line = read_process_line(process, timeout_seconds=8)
    if not line:
        _stdout, stderr = process.communicate(timeout=2)
        raise RuntimeError("local API bridge failed to start: %s" % safe_error_text(stderr))
    try:
        started = json.loads(line)
    except json.JSONDecodeError as exc:
        process.terminate()
        raise RuntimeError("local API bridge returned malformed startup metadata") from exc
    if not started.get("ok"):
        process.terminate()
        raise RuntimeError("local API bridge failed to start")
    return {
        "host": started["host"],
        "port": started["port"],
        "pid": process.pid,
    }


def read_process_line(process: subprocess.Popen, timeout_seconds: int) -> str:
    if process.stdout is None:
        return ""
    output: List[str] = []

    def read_line() -> None:
        output.append(process.stdout.readline())

    thread = threading.Thread(target=read_line, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if not output:
        process.terminate()
        return ""
    return output[0].strip()


def local_api_pythonpath(existing: str) -> str:
    repo_root = Path(__file__).resolve().parents[3]
    paths = [
        repo_root / "local-api" / "src",
        repo_root / "cli" / "src",
        repo_root / "sdk-python" / "src",
        repo_root / "policy-engine" / "src",
    ]
    values = [str(path) for path in paths if path.exists()]
    if existing:
        values.append(existing)
    return os.pathsep.join(values)


def origin_from_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("console URL must include scheme and host")
    return "%s://%s" % (parsed.scheme, parsed.netloc)


def safe_error_text(value: str) -> str:
    first = (value or "").splitlines()[0] if value else ""
    return first or "unknown error"


def build_capsule_manifest(
    args: argparse.Namespace,
    source_dir: Path,
    policy_path: Path,
    policy: Dict[str, Any],
) -> Dict[str, Any]:
    container_digest = args.container_digest or os.environ.get("AGENT_CAPSULE_CONTAINER_DIGEST") or None
    if container_digest and not HASH_PATTERN.match(container_digest):
        raise ValueError("container digest must be sha256:<64 hex chars>")

    dependency_hashes = dependency_lockfile_hashes(source_dir, args.dependency_lockfile)
    prompt_template_hashes = prompt_template_hashes_from_args(source_dir, args.prompt_template)
    tool_definitions = tool_definitions_from_args(source_dir, args.tool_schema)
    model_configuration = model_configuration_from_args(source_dir, args.model_provider, args.model, args.model_config)
    signing_key = signing_key_bytes(args.signing_key)

    manifest = {
        "manifest_version": 1,
        "agent_name": args.agent_name or policy.get("agent", {}).get("name") or source_dir.resolve().name,
        "agent_version": args.agent_version,
        "language": args.language,
        "runtime_version": args.runtime_version or runtime_version(args.language),
        "sdk_version": args.sdk_version,
        "container_digest": container_digest,
        "dependency_hashes": dependency_hashes,
        "prompt_template_hashes": prompt_template_hashes,
        "tool_definitions": tool_definitions,
        "model_configuration": model_configuration,
        "policy_hash": hash_file(policy_path),
        "policy_version": policy["version"],
        "network_destinations": network_destinations_from_policy(policy),
        "required_secrets": sorted(set(args.required_secret)),
        "usage_meters": usage_meters_from_args(args.usage_meter),
        "signature": {
            "algorithm": "hmac-sha256",
            "key_id": args.key_id,
            "value": "",
        },
    }
    manifest["signature"]["value"] = sign_manifest(manifest, signing_key)
    return manifest


def dependency_lockfile_hashes(source_dir: Path, explicit_paths: List[str]) -> Dict[str, str]:
    paths = [resolve_input_path(source_dir, item) for item in explicit_paths]
    if not paths:
        paths = [
            source_dir / filename
            for filename in KNOWN_LOCKFILES
            if (source_dir / filename).exists()
        ]
    hashes = {}
    for path in sorted(unique_paths(paths), key=lambda item: path_key(source_dir, item)):
        if not path.exists() or not path.is_file():
            raise ValueError("dependency lockfile not found: %s" % path)
        hashes[path_key(source_dir, path)] = hash_file(path)
    return hashes


def prompt_template_hashes_from_args(source_dir: Path, values: List[str]) -> Dict[str, str]:
    hashes = {}
    for value in values:
        name, path = parse_named_path(source_dir, value)
        hashes[name] = hash_file(path)
    return dict(sorted(hashes.items()))


def tool_definitions_from_args(source_dir: Path, values: List[str]) -> List[Dict[str, str]]:
    definitions = []
    for value in values:
        parts = value.split(":", 2)
        if len(parts) != 3:
            raise ValueError("tool schema must use NAME:VERSION:PATH")
        name, version, path_text = parts
        path = resolve_input_path(source_dir, path_text)
        if not path.exists() or not path.is_file():
            raise ValueError("tool schema file not found: %s" % path)
        definitions.append({
            "name": name,
            "version": version,
            "schema_hash": hash_file(path),
        })
    return sorted(definitions, key=lambda item: (item["name"], item["version"]))


def model_configuration_from_args(
    source_dir: Path,
    provider: str,
    model: str,
    config_path_text: Optional[str],
) -> Dict[str, str]:
    if config_path_text:
        config_path = resolve_input_path(source_dir, config_path_text)
        if not config_path.exists() or not config_path.is_file():
            raise ValueError("model config file not found: %s" % config_path)
        configuration_hash = hash_file(config_path)
    else:
        configuration_hash = hash_value({"provider": provider, "model": model})
    return {
        "provider": provider,
        "model": model,
        "configuration_hash": configuration_hash,
    }


def network_destinations_from_policy(policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    destinations = []
    for destination_id, destination in policy.get("destinations", {}).items():
        destinations.append({
            "id": destination_id,
            "type": destination.get("type"),
            "domain": destination.get("domain"),
            "risk": destination.get("risk"),
        })
    return sorted(destinations, key=lambda item: item["id"])


def usage_meters_from_args(values: List[str]) -> List[Dict[str, str]]:
    meters = []
    for value in values:
        parts = value.split(":", 1)
        if len(parts) != 2:
            raise ValueError("usage meter must use NAME:UNIT")
        meters.append({"name": parts[0], "unit": parts[1]})
    return sorted(meters, key=lambda item: item["name"])


def sign_manifest(manifest: Dict[str, Any], signing_key: bytes) -> str:
    unsigned = dict(manifest)
    unsigned["signature"] = {
        "algorithm": manifest["signature"]["algorithm"],
        "key_id": manifest["signature"]["key_id"],
        "value": "",
    }
    digest = hmac.new(signing_key, canonical_json(unsigned).encode("utf-8"), hashlib.sha256).hexdigest()
    return "hmac-sha256:%s" % digest


def signing_key_bytes(value: Optional[str]) -> bytes:
    if value:
        candidate = Path(value)
        if candidate.exists() and candidate.is_file():
            return candidate.read_bytes().strip()
        return value.encode("utf-8")

    env_key = os.environ.get("AGENT_CAPSULE_SIGNING_KEY")
    if env_key:
        return env_key.encode("utf-8")

    key_path = Path(DEFAULT_CAPSULE_DIR) / "signing.key"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if key_path.exists():
        return key_path.read_bytes().strip()
    key = secrets.token_hex(32).encode("utf-8")
    key_path.write_bytes(key)
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass
    return key


def build_manifest_report(manifest: Dict[str, Any], output_path: Path, source_dir: Path) -> Dict[str, Any]:
    return {
        "ok": True,
        "manifest": str(output_path),
        "manifest_hash": hash_value(manifest),
        "source_dir": str(source_dir),
        "package_managers": detected_package_managers(manifest["dependency_hashes"]),
        "dependency_hashes": manifest["dependency_hashes"],
        "prompt_template_names": sorted(manifest["prompt_template_hashes"].keys()),
        "tool_names": [tool["name"] for tool in manifest["tool_definitions"]],
        "signature": {
            "algorithm": manifest["signature"]["algorithm"],
            "key_id": manifest["signature"]["key_id"],
            "present": bool(manifest["signature"]["value"]),
        },
    }


def validate_manifest_object(manifest: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    required = [
        "manifest_version",
        "agent_name",
        "agent_version",
        "language",
        "runtime_version",
        "sdk_version",
        "container_digest",
        "dependency_hashes",
        "prompt_template_hashes",
        "tool_definitions",
        "model_configuration",
        "policy_hash",
        "policy_version",
        "network_destinations",
        "required_secrets",
        "usage_meters",
        "signature",
    ]
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    for key in required:
        if key not in manifest:
            errors.append("missing required key %s" % key)

    if errors:
        return errors
    if manifest["language"] not in ("python", "typescript", "java", "go", "rust"):
        errors.append("language is unsupported")
    if manifest["container_digest"] is not None and not _is_hash(manifest["container_digest"]):
        errors.append("container_digest must be sha256:<64 hex chars> or null")
    for name, value in manifest.get("dependency_hashes", {}).items():
        if not _is_hash(value):
            errors.append("dependency hash for %s is invalid" % name)
    for name, value in manifest.get("prompt_template_hashes", {}).items():
        if not _is_hash(value):
            errors.append("prompt template hash for %s is invalid" % name)
    for item in manifest.get("tool_definitions", []):
        if not isinstance(item, dict) or not item.get("name") or not item.get("version") or not _is_hash(item.get("schema_hash")):
            errors.append("tool definition is invalid")
    model_config = manifest.get("model_configuration", {})
    if not isinstance(model_config, dict) or not model_config.get("provider") or not model_config.get("model"):
        errors.append("model_configuration is invalid")
    elif not _is_hash(model_config.get("configuration_hash")):
        errors.append("model_configuration.configuration_hash is invalid")
    if not _is_hash(manifest.get("policy_hash")):
        errors.append("policy_hash is invalid")
    if not isinstance(manifest.get("policy_version"), int) or isinstance(manifest.get("policy_version"), bool):
        errors.append("policy_version must be an integer")
    for destination in manifest.get("network_destinations", []):
        if not isinstance(destination, dict):
            errors.append("network destination is invalid")
            continue
        for key in ("id", "type", "risk"):
            if not destination.get(key):
                errors.append("network destination missing %s" % key)
    signature = manifest.get("signature")
    if not isinstance(signature, dict):
        errors.append("signature must be an object")
    else:
        if not signature.get("algorithm"):
            errors.append("signature.algorithm is required")
        if not signature.get("key_id"):
            errors.append("signature.key_id is required")
        if not signature.get("value"):
            errors.append("signature.value is required")
    return errors


def collect_ci_trace_paths(args: argparse.Namespace) -> List[Path]:
    paths: List[Path] = []
    for value in args.trace:
        paths.extend(expand_trace_path(Path(value)))
    if args.trace_dir:
        paths.extend(expand_trace_path(Path(args.trace_dir)))
    return sorted(unique_paths(paths), key=lambda item: str(item))


def expand_trace_path(path: Path) -> List[Path]:
    if not path.exists() or path.is_file():
        return [path]
    metadata_dir = path / "metadata"
    search_dir = metadata_dir if metadata_dir.exists() else path
    return sorted(search_dir.glob("*.json"))


def ci_findings_from_privacy_map(privacy_map: Dict[str, Any], trace_path: Path) -> List[Dict[str, Any]]:
    findings = []
    for finding in privacy_map.get("findings", []):
        kind = finding.get("kind")
        if kind == "undeclared_high_risk_egress":
            findings.append(ci_finding(
                code="undeclared_high_risk_egress",
                message="Undeclared high-risk egress remains for destination %s." % finding.get("destination_id"),
                path=trace_path,
                trace_id=privacy_map.get("trace_id"),
                destination_id=finding.get("destination_id"),
                risk=finding.get("risk"),
                data_classes=finding.get("data_classes", []),
            ))
        elif kind == "undeclared_destination":
            findings.append(ci_finding(
                code="undeclared_destination",
                message="Destination %s appears in traces but is not declared in policy." % finding.get("destination_id"),
                path=trace_path,
                trace_id=privacy_map.get("trace_id"),
                destination_id=finding.get("destination_id"),
                risk=finding.get("risk"),
                data_classes=finding.get("data_classes", []),
            ))
    return findings


def ci_undeclared_destination_findings(
    policy: Dict[str, Any],
    trace: Dict[str, Any],
    trace_path: Path,
) -> List[Dict[str, Any]]:
    declared = set(policy.get("destinations", {}).keys())
    destination_ids = set()
    for destination in trace.get("destinations", []):
        if isinstance(destination, dict) and destination.get("id"):
            destination_ids.add(destination["id"])
    for span in trace.get("spans", []):
        if isinstance(span, dict) and span.get("destination_id"):
            destination_ids.add(span["destination_id"])

    findings = []
    for destination_id in sorted(destination_ids - declared):
        observed_data = observed_data_for_destination(trace, destination_id)
        destination_risk = trace_destination_lookup(trace).get(destination_id, {}).get("risk", "medium")
        findings.append(ci_finding(
            code="undeclared_destination",
            message="Destination %s appears in traces but is not declared in policy." % destination_id,
            path=trace_path,
            trace_id=trace.get("trace_id"),
            destination_id=destination_id,
            risk=destination_risk,
            data_classes=observed_data,
        ))
    return findings


def ci_high_risk_unapproved_findings(
    policy: Dict[str, Any],
    trace: Dict[str, Any],
    trace_path: Path,
) -> List[Dict[str, Any]]:
    findings = []
    for span in trace.get("spans", []):
        if not isinstance(span, dict) or not span.get("destination_id"):
            continue
        high_risk_data = high_risk_data_classes(span.get("data_classes", []))
        if not high_risk_data:
            continue
        if ci_span_is_approved(policy, trace, span):
            continue
        findings.append(ci_finding(
            code="high_risk_unapproved_destination",
            message="High-risk data classes reach destination %s without an approved policy action." % span.get("destination_id"),
            path=trace_path,
            trace_id=trace.get("trace_id"),
            destination_id=span.get("destination_id"),
            risk=classify_data_risk(high_risk_data),
            data_classes=high_risk_data,
        ))
    return findings


def ci_span_is_approved(policy: Dict[str, Any], trace: Dict[str, Any], span: Dict[str, Any]) -> bool:
    destination_id = span.get("destination_id")
    if destination_id not in policy.get("destinations", {}):
        return False
    decision = evaluate_policy(
        policy,
        destination_id=destination_id,
        destination_risk=destination_risk_for_span(policy, trace, destination_id),
        data_classes=span.get("data_classes", []),
        fields=span.get("data_classes", []),
        mode="guard",
    )
    return decision.action in ("allow", "allow_fields", "redact", "require_approval")


def high_risk_data_classes(data_classes: List[str]) -> List[str]:
    return sorted({
        data_class
        for data_class in data_classes
        if classify_data_risk([data_class]) in ("high", "critical")
    })


def observed_data_for_destination(trace: Dict[str, Any], destination_id: str) -> List[str]:
    observed = set()
    for destination in trace.get("destinations", []):
        if isinstance(destination, dict) and destination.get("id") == destination_id:
            observed.update(destination.get("observed_data_classes", []))
    for span in trace.get("spans", []):
        if isinstance(span, dict) and span.get("destination_id") == destination_id:
            observed.update(span.get("data_classes", []))
    return sorted(observed)


def trace_destination_lookup(trace: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        destination["id"]: destination
        for destination in trace.get("destinations", [])
        if isinstance(destination, dict) and destination.get("id")
    }


def destination_risk_for_span(policy: Dict[str, Any], trace: Dict[str, Any], destination_id: str) -> str:
    trace_destination = trace_destination_lookup(trace).get(destination_id, {})
    policy_destination = policy.get("destinations", {}).get(destination_id, {})
    return trace_destination.get("risk") or policy_destination.get("risk") or "medium"


def ci_manifest_findings(args: argparse.Namespace) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    if not args.manifest:
        if args.release:
            findings.append(ci_finding(
                code="manifest_required",
                message="Release builds require a capsule manifest.",
                path=None,
            ))
        return findings

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        findings.append(ci_finding(
            code="manifest_missing",
            message="Capsule manifest was not found.",
            path=manifest_path,
        ))
        return findings

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        findings.append(ci_finding(
            code="manifest_malformed",
            message="Capsule manifest JSON is malformed.",
            path=manifest_path,
        ))
        return findings

    validation_errors = validate_manifest_object(manifest)
    for error in validation_errors:
        findings.append(ci_finding(
            code="manifest_invalid",
            message="Capsule manifest is invalid: %s" % error,
            path=manifest_path,
        ))

    if args.release:
        signature = manifest.get("signature") if isinstance(manifest, dict) else None
        if not isinstance(signature, dict) or not signature.get("value"):
            findings.append(ci_finding(
                code="manifest_signature_missing",
                message="Release builds require a manifest signature value.",
                path=manifest_path,
            ))
        supported, reason = release_runtime_supported(manifest)
        if not supported:
            findings.append(ci_finding(
                code="runtime_unsupported",
                message=reason,
                path=manifest_path,
            ))

    return findings


def release_runtime_supported(manifest: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(manifest, dict):
        return False, "Release builds require a manifest object."
    language = manifest.get("language")
    runtime = str(manifest.get("runtime_version") or "")
    if language == "python":
        match = re.search(r"(\d+)\.(\d+)", runtime)
        if not match:
            return False, "Release builds require a parseable Python runtime version."
        major = int(match.group(1))
        minor = int(match.group(2))
        if (major, minor) < (3, 10):
            return False, "Release builds require Python 3.10 or newer."
        return True, ""
    if language in ("typescript", "java", "go", "rust"):
        if runtime and runtime != "unknown":
            return True, ""
        return False, "Release builds require a concrete %s runtime version." % language
    return False, "Release builds use an unsupported runtime language."


def load_demo_manifest(manifest_path: Path) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    findings: List[Dict[str, Any]] = []
    if not manifest_path.exists():
        return None, [demo_finding("manifest_missing", "Signed capsule manifest was not found.", manifest_path)]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, [demo_finding("manifest_malformed", "Capsule manifest JSON is malformed.", manifest_path)]

    validation_errors = validate_manifest_object(manifest)
    for error in validation_errors:
        findings.append(demo_finding("manifest_invalid", "Capsule manifest is invalid: %s" % error, manifest_path))
    if isinstance(manifest, dict):
        signature = manifest.get("signature")
        if not isinstance(signature, dict) or not signature.get("value"):
            findings.append(demo_finding("manifest_signature_missing", "Confidential demos require a signed manifest.", manifest_path))
        supported, reason = release_runtime_supported(manifest)
        if not supported:
            findings.append(demo_finding("runtime_unsupported", reason, manifest_path))
    return manifest if isinstance(manifest, dict) else None, findings


def validate_demo_manifest_policy(
    manifest: Dict[str, Any],
    manifest_path: Path,
    policy: Dict[str, Any],
    policy_path: Path,
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    actual_policy_hash = hash_file(policy_path)
    if manifest.get("policy_hash") != actual_policy_hash:
        findings.append(demo_finding(
            "manifest_policy_hash_mismatch",
            "Manifest policy hash does not match the selected policy file.",
            manifest_path,
        ))
    if manifest.get("policy_version") != policy.get("version"):
        findings.append(demo_finding(
            "manifest_policy_version_mismatch",
            "Manifest policy version does not match the selected policy file.",
            manifest_path,
        ))

    declared_destinations = set(policy.get("destinations", {}).keys())
    manifest_destinations = {
        destination.get("id")
        for destination in manifest.get("network_destinations", [])
        if isinstance(destination, dict) and destination.get("id")
    }
    for destination_id in sorted(manifest_destinations - declared_destinations):
        findings.append(demo_finding(
            "manifest_destination_not_in_policy",
            "Manifest destination %s is not declared in the selected policy." % destination_id,
            manifest_path,
            destination_id=destination_id,
        ))
    for destination_id in sorted(declared_destinations - manifest_destinations):
        findings.append(demo_finding(
            "policy_destination_missing_from_manifest",
            "Policy destination %s is missing from manifest network destinations." % destination_id,
            manifest_path,
            destination_id=destination_id,
        ))
    return findings


def validate_demo_privacy(policy: Dict[str, Any], trace_paths: List[Path]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for trace_path in trace_paths:
        if not trace_path.exists():
            findings.append(demo_finding("trace_missing", "Trace metadata file was not found.", trace_path))
            continue
        try:
            trace = load_trace_file(trace_path)
        except PolicyEngineError as exc:
            findings.append(demo_finding("trace_malformed", "Trace metadata is malformed: %s" % exc, trace_path))
            continue
        privacy_map = generate_privacy_map(trace, policy)
        for finding in privacy_map.get("findings", []):
            if finding.get("kind") == "undeclared_high_risk_egress":
                findings.append(demo_finding(
                    "undeclared_high_risk_egress",
                    "Confidential demos cannot start while undeclared high-risk egress remains.",
                    trace_path,
                    destination_id=finding.get("destination_id"),
                    risk=finding.get("risk"),
                    data_classes=finding.get("data_classes", []),
                ))
            elif finding.get("kind") == "undeclared_destination":
                findings.append(demo_finding(
                    "undeclared_destination",
                    "Trace destination %s is not declared in policy." % finding.get("destination_id"),
                    trace_path,
                    destination_id=finding.get("destination_id"),
                    risk=finding.get("risk"),
                    data_classes=finding.get("data_classes", []),
                ))
    return dedupe_ci_findings(findings)


def demo_environment(
    args: argparse.Namespace,
    manifest_path: Path,
    manifest: Optional[Dict[str, Any]],
    created_at: str,
    preflight_ok: bool,
) -> Dict[str, Any]:
    manifest_hash = hash_file(manifest_path) if manifest_path.exists() else None
    return {
        "provider": args.environment_provider,
        "mode": args.mode,
        "status": "started" if preflight_ok else "not_started",
        "confidentiality": "confidential-like local verification",
        "hosted_confidential_hardware": False,
        "started_at": created_at if preflight_ok else None,
        "runtime": {
            "language": manifest.get("language") if manifest else None,
            "version": manifest.get("runtime_version") if manifest else None,
            "supported": release_runtime_supported(manifest)[0] if manifest else False,
        },
        "manifest_hash": manifest_hash,
    }


def capture_demo_attestation(
    args: argparse.Namespace,
    manifest: Dict[str, Any],
    manifest_path: Path,
    demo_dir: Path,
    environment: Dict[str, Any],
) -> Dict[str, Any]:
    manifest_hash = hash_file(manifest_path)
    if args.attestation_evidence:
        evidence_path = Path(args.attestation_evidence)
        try:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            evidence = {
                "provider": args.environment_provider,
                "status": "failed",
                "reason": "attestation evidence JSON is malformed",
            }
    else:
        evidence = {
            "provider": args.environment_provider,
            "status": "verified",
            "manifest_hash": manifest_hash,
            "runtime_language": manifest.get("language"),
            "runtime_version": manifest.get("runtime_version"),
            "environment": environment.get("provider"),
        }

    provider = str(evidence.get("provider") or args.environment_provider)
    status = str(evidence.get("status") or "failed")
    reasons = []
    if provider not in SUPPORTED_DEMO_ENVIRONMENTS:
        reasons.append("unsupported attestation provider")
    if status != "verified":
        reasons.append(str(evidence.get("reason") or "attestation status is not verified"))
    evidence_manifest_hash = evidence.get("manifest_hash")
    if evidence_manifest_hash is not None and evidence_manifest_hash != manifest_hash:
        reasons.append("attestation manifest hash does not match")
    evidence_runtime = evidence.get("runtime_version")
    if evidence_runtime is not None and evidence_runtime != manifest.get("runtime_version"):
        reasons.append("attestation runtime version does not match")

    safe_attestation = {
        "provider": provider,
        "status": status,
        "verified": not reasons,
        "captured_at": utc_now(),
        "evidence_hash": hash_value(evidence),
        "manifest_hash": manifest_hash,
        "runtime_language": evidence.get("runtime_language") or manifest.get("language"),
        "runtime_version": evidence.get("runtime_version") or manifest.get("runtime_version"),
        "reasons": reasons,
    }
    (demo_dir / "attestation-result.json").write_text(
        json.dumps(safe_attestation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return safe_attestation


def skipped_demo_attestation(args: argparse.Namespace, manifest_path: Path, demo_dir: Path) -> Dict[str, Any]:
    safe_attestation = {
        "provider": args.environment_provider,
        "status": "skipped",
        "verified": False,
        "captured_at": utc_now(),
        "evidence_hash": None,
        "manifest_hash": hash_file(manifest_path) if manifest_path.exists() else None,
        "runtime_language": None,
        "runtime_version": None,
        "reasons": ["preflight failed"],
    }
    (demo_dir / "attestation-result.json").write_text(
        json.dumps(safe_attestation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return safe_attestation


def release_demo_secrets(
    args: argparse.Namespace,
    manifest: Dict[str, Any],
    attestation: Dict[str, Any],
) -> Dict[str, Any]:
    required = sorted(set(manifest.get("required_secrets", [])))
    configured = configured_secret_names(args, required)
    missing = sorted(set(required) - configured)
    released = bool(attestation.get("verified")) and not missing
    receipt_basis = {
        "provider": args.secret_provider,
        "required_secret_names": required,
        "released_secret_names": required if released else [],
        "missing_secret_names": missing,
        "attestation_evidence_hash": attestation.get("evidence_hash"),
        "released": released,
    }
    return {
        "provider": args.secret_provider,
        "released": released,
        "status": "released" if released else "blocked",
        "required_secret_names": required,
        "released_secret_names": required if released else [],
        "missing_secret_names": missing,
        "released_after_attestation": bool(attestation.get("verified")),
        "receipt_hash": hash_value(receipt_basis),
    }


def blocked_secret_release(
    manifest: Optional[Dict[str, Any]],
    provider: str,
    reason: str,
) -> Dict[str, Any]:
    required = sorted(set(manifest.get("required_secrets", []))) if manifest else []
    return {
        "provider": provider,
        "released": False,
        "status": "blocked",
        "required_secret_names": required,
        "released_secret_names": [],
        "missing_secret_names": required,
        "released_after_attestation": False,
        "receipt_hash": hash_value({"provider": provider, "required_secret_names": required, "reason": reason}),
    }


def configured_secret_names(args: argparse.Namespace, required: List[str]) -> set:
    if args.secret_provider == "none":
        return set()
    if args.secret_provider == "env":
        return {name for name in required if os.environ.get(name)}

    configured = set()
    for name in args.secret:
        if "=" in name:
            raise ValueError("pass secret names only; do not pass secret values")
        configured.add(name)
    return configured


def safe_manifest_summary(manifest: Dict[str, Any], manifest_path: Path) -> Dict[str, Any]:
    signature = manifest.get("signature", {}) if isinstance(manifest.get("signature"), dict) else {}
    return {
        "path": str(manifest_path),
        "manifest_hash": hash_file(manifest_path) if manifest_path.exists() else hash_value(manifest),
        "agent_name": manifest.get("agent_name"),
        "agent_version": manifest.get("agent_version"),
        "language": manifest.get("language"),
        "runtime_version": manifest.get("runtime_version"),
        "sdk_version": manifest.get("sdk_version"),
        "container_digest": manifest.get("container_digest"),
        "policy_hash": manifest.get("policy_hash"),
        "policy_version": manifest.get("policy_version"),
        "network_destinations": manifest.get("network_destinations", []),
        "required_secrets": manifest.get("required_secrets", []),
        "usage_meters": manifest.get("usage_meters", []),
        "model_configuration": manifest.get("model_configuration", {}),
        "tool_definitions": manifest.get("tool_definitions", []),
        "signature": {
            "algorithm": signature.get("algorithm"),
            "key_id": signature.get("key_id"),
            "present": bool(signature.get("value")),
        },
    }


def safe_policy_summary(policy: Dict[str, Any], policy_path: Path) -> Dict[str, Any]:
    destinations = []
    for destination_id, destination in sorted(policy.get("destinations", {}).items()):
        destinations.append({
            "id": destination_id,
            "type": destination.get("type"),
            "domain": destination.get("domain"),
            "risk": destination.get("risk"),
            "allowed_data": destination.get("allowed_data", []),
            "redact": destination.get("redact", []),
            "require_approval": destination.get("require_approval", []),
        })
    return {
        "path": str(policy_path),
        "policy_hash": hash_file(policy_path),
        "version": policy.get("version"),
        "agent_name": policy.get("agent", {}).get("name"),
        "owner": policy.get("agent", {}).get("owner"),
        "destinations": destinations,
        "defaults": policy.get("defaults", {}),
    }


def demo_privacy_summary(policy: Dict[str, Any], trace_paths: List[Path]) -> List[Dict[str, Any]]:
    summaries = []
    for trace_path in trace_paths:
        if not trace_path.exists():
            continue
        try:
            trace = load_trace_file(trace_path)
        except PolicyEngineError:
            continue
        privacy_map = generate_privacy_map(trace, policy)
        summaries.append({
            "trace_id": privacy_map.get("trace_id"),
            "run_id": privacy_map.get("run_id"),
            "destinations": privacy_map.get("destinations", []),
            "finding_count": len(privacy_map.get("findings", [])),
        })
    return summaries


def build_vendor_telemetry(
    ok: bool,
    customer: str,
    created_at: str,
    manifest: Dict[str, Any],
    policy: Dict[str, Any],
    environment: Dict[str, Any],
    attestation: Dict[str, Any],
    secret_release: Dict[str, Any],
    trace_paths: List[Path],
    findings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "ok": ok,
        "customer": customer,
        "created_at": created_at,
        "health": "ready" if ok else "blocked",
        "agent": {
            "name": manifest.get("agent_name"),
            "version": manifest.get("agent_version"),
            "language": manifest.get("language"),
            "runtime_version": manifest.get("runtime_version"),
            "sdk_version": manifest.get("sdk_version"),
        },
        "policy": {
            "version": policy.get("version"),
            "hash": policy.get("policy_hash"),
            "destination_count": len(policy.get("destinations", [])),
        },
        "environment": environment,
        "attestation": {
            "provider": attestation.get("provider"),
            "status": attestation.get("status"),
            "verified": attestation.get("verified"),
            "evidence_hash": attestation.get("evidence_hash"),
        },
        "secret_release": {
            "provider": secret_release.get("provider"),
            "released": secret_release.get("released"),
            "required_secret_names": secret_release.get("required_secret_names", []),
            "missing_secret_names": secret_release.get("missing_secret_names", []),
            "receipt_hash": secret_release.get("receipt_hash"),
        },
        "usage_meters": manifest.get("usage_meters", []),
        "trace_summaries": safe_trace_summaries(trace_paths),
        "finding_codes": [finding.get("code") for finding in findings],
    }


def safe_trace_summaries(trace_paths: List[Path]) -> List[Dict[str, Any]]:
    summaries = []
    for trace_path in trace_paths:
        if not trace_path.exists():
            continue
        try:
            trace = load_trace_file(trace_path)
        except PolicyEngineError:
            continue
        spans = []
        for span in trace.get("spans", []):
            if not isinstance(span, dict):
                continue
            decision = span.get("policy_decision", {}) if isinstance(span.get("policy_decision"), dict) else {}
            error_summary = span.get("error_summary") if isinstance(span.get("error_summary"), dict) else None
            spans.append({
                "span_id": span.get("span_id"),
                "component_type": span.get("component_type"),
                "component_name": span.get("component_name"),
                "status": span.get("status"),
                "destination_id": span.get("destination_id"),
                "payload_size_bytes": span.get("payload_size_bytes"),
                "token_count": span.get("token_count"),
                "content_hash": span.get("content_hash"),
                "data_classes": span.get("data_classes", []),
                "policy_decision": {
                    "action": decision.get("action"),
                    "reason": decision.get("reason"),
                    "policy_version": decision.get("policy_version"),
                    "fields": decision.get("fields", []),
                },
                "error_summary": {
                    "type": error_summary.get("type"),
                    "message": error_summary.get("message"),
                    "stack_hash": error_summary.get("stack_hash"),
                } if error_summary else None,
            })
        summaries.append({
            "path": str(trace_path),
            "trace_id": trace.get("trace_id"),
            "run_id": trace.get("run_id"),
            "mode": trace.get("mode"),
            "created_at": trace.get("created_at"),
            "span_count": len(spans),
            "spans": spans,
        })
    return summaries


def build_support_bundle(
    customer: str,
    created_at: str,
    manifest: Dict[str, Any],
    policy: Dict[str, Any],
    environment: Dict[str, Any],
    attestation: Dict[str, Any],
    secret_release: Dict[str, Any],
    findings: List[Dict[str, Any]],
    telemetry_path: Path,
    verification_page_path: Path,
) -> Dict[str, Any]:
    return {
        "ok": False,
        "customer": customer,
        "created_at": created_at,
        "findings": findings,
        "manifest": manifest,
        "policy": policy,
        "environment": environment,
        "attestation": attestation,
        "secret_release": secret_release,
        "artifacts": {
            "vendor_telemetry": str(telemetry_path),
            "customer_verification_page": str(verification_page_path),
        },
        "privacy": {
            "raw_payloads_included": False,
            "secret_values_included": False,
            "manifest_signature_value_included": False,
        },
    }


def render_customer_verification_page(
    customer: str,
    ok: bool,
    manifest: Dict[str, Any],
    policy: Dict[str, Any],
    environment: Dict[str, Any],
    attestation: Dict[str, Any],
    secret_release: Dict[str, Any],
    privacy_summary: List[Dict[str, Any]],
    findings: List[Dict[str, Any]],
) -> str:
    allowed_plaintext = sorted({
        data_class
        for destination in policy.get("destinations", [])
        for data_class in destination.get("allowed_data", [])
    })
    redacted = sorted({
        data_class
        for destination in policy.get("destinations", [])
        for data_class in destination.get("redact", [])
    })
    approvals = sorted({
        data_class
        for destination in policy.get("destinations", [])
        for data_class in destination.get("require_approval", [])
    })
    destinations = policy.get("destinations", [])
    tools = [item for item in destinations if item.get("type") == "external_tool"]
    models = [item for item in destinations if item.get("type") == "model_provider"]
    status = "Ready" if ok else "Blocked"
    finding_items = "".join("<li>%s: %s</li>" % (escape(str(item.get("code"))), escape(str(item.get("message")))) for item in findings) or "<li>None</li>"

    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Agent Capsule Verification - {customer}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #17202a; margin: 40px; line-height: 1.5; }}
    h1, h2 {{ font-weight: 400; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; }}
    th, td {{ border: 1px solid #d8dee4; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f6f8fa; font-weight: 400; }}
    .status {{ padding: 8px 12px; border: 1px solid #d8dee4; display: inline-block; }}
  </style>
</head>
<body>
  <h1>Agent Capsule Verification</h1>
  <p class="status">Demo status: {status}</p>
  <h2>Capsule Identity</h2>
  <table>
    <tr><th>Customer</th><td>{customer}</td></tr>
    <tr><th>Agent</th><td>{agent_name} {agent_version}</td></tr>
    <tr><th>Manifest hash</th><td>{manifest_hash}</td></tr>
    <tr><th>Policy version</th><td>{policy_version}</td></tr>
    <tr><th>Runtime</th><td>{language} {runtime_version}</td></tr>
  </table>
  <h2>Attestation</h2>
  <table>
    <tr><th>Provider</th><td>{attestation_provider}</td></tr>
    <tr><th>Status</th><td>{attestation_status}</td></tr>
    <tr><th>Evidence hash</th><td>{attestation_hash}</td></tr>
    <tr><th>Environment</th><td>{environment_provider}</td></tr>
  </table>
  <h2>Approved Model Providers</h2>
  {models}
  <h2>Approved Tools</h2>
  {tools}
  <h2>Approved Network Destinations</h2>
  {destinations}
  <h2>Data Classes</h2>
  <table>
    <tr><th>May leave as plaintext</th><td>{allowed_plaintext}</td></tr>
    <tr><th>Redacted before egress</th><td>{redacted}</td></tr>
    <tr><th>Requires approval</th><td>{approvals}</td></tr>
  </table>
  <h2>Secret Release</h2>
  <table>
    <tr><th>Provider</th><td>{secret_provider}</td></tr>
    <tr><th>Released</th><td>{secret_released}</td></tr>
    <tr><th>Required names</th><td>{required_secrets}</td></tr>
    <tr><th>Receipt hash</th><td>{secret_receipt}</td></tr>
  </table>
  <h2>Privacy Review</h2>
  <p>Privacy maps evaluated: {privacy_map_count}</p>
  <h2>Findings</h2>
  <ul>{finding_items}</ul>
  <p>This page contains safe metadata only. It does not contain prompt content, document text, model outputs, tool payloads, secret values, user identifiers, or manifest signature values.</p>
</body>
</html>
""".format(
        customer=escape(customer),
        status=escape(status),
        agent_name=escape(str(manifest.get("agent_name", ""))),
        agent_version=escape(str(manifest.get("agent_version", ""))),
        manifest_hash=escape(str(manifest.get("manifest_hash", ""))),
        policy_version=escape(str(policy.get("version", ""))),
        language=escape(str(manifest.get("language", ""))),
        runtime_version=escape(str(manifest.get("runtime_version", ""))),
        attestation_provider=escape(str(attestation.get("provider", ""))),
        attestation_status=escape(str(attestation.get("status", ""))),
        attestation_hash=escape(str(attestation.get("evidence_hash", ""))),
        environment_provider=escape(str(environment.get("provider", ""))),
        models=html_table(models, ["id", "domain", "risk"]),
        tools=html_table(tools, ["id", "domain", "risk"]),
        destinations=html_table(destinations, ["id", "type", "domain", "risk"]),
        allowed_plaintext=escape(", ".join(allowed_plaintext) or "None"),
        redacted=escape(", ".join(redacted) or "None"),
        approvals=escape(", ".join(approvals) or "None"),
        secret_provider=escape(str(secret_release.get("provider", ""))),
        secret_released=escape(str(secret_release.get("released", False))),
        required_secrets=escape(", ".join(secret_release.get("required_secret_names", [])) or "None"),
        secret_receipt=escape(str(secret_release.get("receipt_hash", ""))),
        privacy_map_count=escape(str(len(privacy_summary))),
        finding_items=finding_items,
    )


def html_table(rows: List[Dict[str, Any]], columns: List[str]) -> str:
    if not rows:
        return "<p>None</p>"
    header = "".join("<th>%s</th>" % escape(column.replace("_", " ").title()) for column in columns)
    body_rows = []
    for row in rows:
        body_rows.append("<tr>%s</tr>" % "".join("<td>%s</td>" % escape(str(row.get(column, ""))) for column in columns))
    return "<table><tr>%s</tr>%s</table>" % (header, "".join(body_rows))


def demo_finding(
    code: str,
    message: str,
    path: Optional[Path],
    severity: str = "error",
    destination_id: Optional[str] = None,
    risk: Optional[str] = None,
    data_classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return ci_finding(
        code=code,
        message=message,
        path=path,
        severity=severity,
        destination_id=destination_id,
        risk=risk,
        data_classes=data_classes,
    )


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    if not slug:
        raise ValueError("customer id must contain at least one letter or number")
    return slug


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ci_finding(
    code: str,
    message: str,
    path: Optional[Path],
    severity: str = "error",
    trace_id: Optional[str] = None,
    destination_id: Optional[str] = None,
    risk: Optional[str] = None,
    data_classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    finding: Dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
        "path": str(path) if path is not None else None,
    }
    if trace_id:
        finding["trace_id"] = trace_id
    if destination_id:
        finding["destination_id"] = destination_id
    if risk:
        finding["risk"] = risk
    if data_classes:
        finding["data_classes"] = sorted(set(data_classes))
    return finding


def dedupe_ci_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for finding in findings:
        key = (
            finding.get("code"),
            finding.get("path"),
            finding.get("trace_id"),
            finding.get("destination_id"),
            tuple(finding.get("data_classes", [])),
            finding.get("message"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return sorted(deduped, key=lambda item: (
        item.get("path") or "",
        item.get("trace_id") or "",
        item.get("destination_id") or "",
        item.get("code") or "",
    ))


def ci_annotation(finding: Dict[str, Any], annotation_format: str) -> Dict[str, Any]:
    return {
        "format": annotation_format,
        "path": finding.get("path") or "",
        "start_line": 1,
        "end_line": 1,
        "annotation_level": "failure" if finding.get("severity") == "error" else "warning",
        "title": finding.get("code"),
        "message": finding.get("message"),
        "details": {
            "destination_id": finding.get("destination_id"),
            "risk": finding.get("risk"),
            "data_classes": finding.get("data_classes", []),
            "trace_id": finding.get("trace_id"),
        },
    }


def format_ci_findings(findings: List[Dict[str, Any]]) -> str:
    if not findings:
        return "Findings: none"
    lines = ["Findings:"]
    for finding in findings:
        details = []
        if finding.get("path"):
            details.append("path=%s" % finding["path"])
        if finding.get("destination_id"):
            details.append("destination=%s" % finding["destination_id"])
        if finding.get("data_classes"):
            details.append("data=%s" % ",".join(finding["data_classes"]))
        suffix = " %s" % " ".join(details) if details else ""
        lines.append("- [{severity}] {code}{suffix}: {message}".format(
            severity=finding.get("severity"),
            code=finding.get("code"),
            suffix=suffix,
            message=finding.get("message"),
        ))
    return "\n".join(lines)


def detected_package_managers(dependency_hashes: Dict[str, str]) -> List[str]:
    managers = set()
    for path in dependency_hashes:
        name = Path(path).name
        if name in ("requirements.txt", "requirements.lock", "poetry.lock", "uv.lock", "Pipfile.lock"):
            managers.add("python")
        elif name in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock"):
            managers.add("node")
        elif name == "Cargo.lock":
            managers.add("rust")
        elif name == "go.sum":
            managers.add("go")
        elif name == "pom.xml":
            managers.add("java")
    return sorted(managers)


def parse_named_path(source_dir: Path, value: str) -> Tuple[str, Path]:
    if "=" in value:
        name, path_text = value.split("=", 1)
    else:
        path_text = value
        name = Path(path_text).stem
    path = resolve_input_path(source_dir, path_text)
    if not path.exists() or not path.is_file():
        raise ValueError("file not found: %s" % path)
    return name, path


def resolve_input_path(source_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else source_dir / path


def unique_paths(paths: List[Path]) -> List[Path]:
    seen = set()
    result = []
    for path in paths:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def path_key(source_dir: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(source_dir.resolve()))
    except ValueError:
        return str(path)


def runtime_version(language: str) -> str:
    if language == "python":
        return platform.python_version()
    return "unknown"


def hash_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return "sha256:%s" % digest


def hash_value(value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return "sha256:%s" % digest


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and bool(HASH_PATTERN.match(value))


def load_config() -> Dict[str, Any]:
    config_path = Path(DEFAULT_CAPSULE_DIR) / "config.json"
    if not config_path.exists():
        return {
            "trace_dir": DEFAULT_TRACE_DIR,
            "policy_path": DEFAULT_POLICY_PATH,
        }
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError("malformed Agent Capsule config") from exc


def validate_policy_file(policy_path: Path) -> List[str]:
    try:
        policy = load_policy_file(policy_path)
    except PolicyEngineError as exc:
        return [str(exc)]
    return validate_policy_object(policy)


def validate_policy_object(policy: Dict[str, Any]) -> List[str]:
    return engine_validate_policy_object(policy)


def _format_findings(findings: List[Dict[str, Any]]) -> str:
    if not findings:
        return "Findings: none"
    lines = ["Findings:"]
    for finding in findings:
        lines.append(
            "- {kind} destination={destination_id} risk={risk} data={data}".format(
                kind=finding.get("kind"),
                destination_id=finding.get("destination_id"),
                risk=finding.get("risk"),
                data=",".join(finding.get("data_classes", [])),
            )
        )
    return "\n".join(lines)


def _format_suggestions(suggestions: List[Dict[str, Any]]) -> str:
    if not suggestions:
        return "Suggestions: none"
    unique_actions = sorted({item.get("action", "") for item in suggestions if item.get("action")})
    unique_destinations = sorted({item.get("destination_id", "") for item in suggestions if item.get("destination_id")})
    return "Suggested actions for %s: %s" % (", ".join(unique_destinations), ", ".join(unique_actions))


def default_policy_yaml() -> str:
    return """version: 1
agent:
  name: claims-triage
  owner: platform-team

destinations: {}

defaults:
  undeclared_high_risk_egress: block
  undeclared_destination: warn
  secrets: block
"""


def output(args: argparse.Namespace, result: Dict[str, Any], text_lines: List[str]) -> None:
    if getattr(args, "json", False):
        print_json(result)
    else:
        for line in text_lines:
            print(line)


def print_json(value: Dict[str, Any]) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def safe_error(exc: Exception) -> str:
    return str(exc).splitlines()[0]

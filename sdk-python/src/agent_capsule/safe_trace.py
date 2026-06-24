import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from .hashing import content_hash
from .trace_store import EncryptedTraceStore


SAFE_TRACE_VERSION = 1
DEFAULT_CREATED_BY = "local-developer"
DEFAULT_REDACTION_PROFILE = "team_debug"

SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "args",
    "document_text",
    "input",
    "model_output",
    "output",
    "payload",
    "prompt",
    "raw_payload",
    "result",
    "secret",
    "secrets",
    "tool_payload",
}

SENSITIVE_VALUE_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
]


class SafeTraceError(ValueError):
    pass


def export_safe_trace_from_store(
    store: EncryptedTraceStore,
    run_id: str,
    created_by: str = DEFAULT_CREATED_BY,
    redaction_profile: str = DEFAULT_REDACTION_PROFILE,
) -> Dict[str, Any]:
    trace = store.find_trace_by_run_id(run_id)
    if trace is None:
        raise SafeTraceError("trace not found for run_id: %s" % run_id)
    return build_safe_trace(
        trace=trace,
        payload_index=_load_payload_index(store, trace["trace_id"]),
        created_by=created_by,
        redaction_profile=redaction_profile,
    )


def build_safe_trace(
    trace: Dict[str, Any],
    payload_index: Optional[Sequence[Dict[str, Any]]] = None,
    created_by: str = DEFAULT_CREATED_BY,
    redaction_profile: str = DEFAULT_REDACTION_PROFILE,
) -> Dict[str, Any]:
    spans = trace.get("spans", [])
    safe_trace = {
        "safe_trace_version": SAFE_TRACE_VERSION,
        "source_trace_id": trace["trace_id"],
        "created_at": _now(),
        "created_by": _safe_created_by(created_by),
        "redaction_profile": redaction_profile,
        "workflow_graph": _workflow_graph(spans),
        "spans": [_safe_span(span) for span in spans],
        "component_versions": _component_versions(trace),
        "policy_decisions": _policy_decisions(spans),
        "content_hashes": _content_hashes(spans, payload_index or []),
        "redaction_markers": _redaction_markers(spans),
        "diagnostic_summary": _diagnostic_summary(spans),
    }
    findings = scan_safe_trace(safe_trace)
    if findings:
        raise SafeTraceError("safe trace scanner found plaintext risk: %s" % "; ".join(findings))
    return safe_trace


def scan_safe_trace(safe_trace: Dict[str, Any], forbidden_values: Optional[Iterable[str]] = None) -> List[str]:
    findings: List[str] = []
    forbidden = [value for value in (forbidden_values or []) if value]
    stack = [("$", safe_trace)]

    while stack:
        path, value = stack.pop()
        if isinstance(value, dict):
            for key, child in value.items():
                normalized_key = str(key).lower()
                if normalized_key in SENSITIVE_KEYS:
                    findings.append("%s contains reserved sensitive key %s" % (path, key))
                stack.append(("%s.%s" % (path, key), child))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                stack.append(("%s[%s]" % (path, index), child))
        elif isinstance(value, str):
            for pattern in SENSITIVE_VALUE_PATTERNS:
                if pattern.search(value):
                    findings.append("%s contains sensitive-looking plaintext" % path)
                    break
            for forbidden_value in forbidden:
                if forbidden_value in value:
                    findings.append("%s contains forbidden plaintext value" % path)
                    break

    return sorted(set(findings))


def _load_payload_index(store: EncryptedTraceStore, trace_id: str) -> List[Dict[str, Any]]:
    index_path = store.index_path(trace_id)
    if not index_path.exists():
        return []
    try:
        value = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return value if isinstance(value, list) else []


def _workflow_graph(spans: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    nodes = []
    edges = []
    for span in spans:
        span_id = span.get("span_id")
        if not span_id:
            continue
        nodes.append({
            "id": span_id,
            "label": span.get("component_name", "unknown"),
            "component_type": span.get("component_type", "unknown"),
        })
        parent_span_id = span.get("parent_span_id")
        if parent_span_id:
            edges.append({"from": parent_span_id, "to": span_id})
    return {"nodes": nodes, "edges": edges}


def _safe_span(span: Dict[str, Any]) -> Dict[str, Any]:
    decision = span.get("policy_decision") or {}
    return {
        "span_id": span.get("span_id", "unknown"),
        "component_type": span.get("component_type", "unknown"),
        "component_name": span.get("component_name", "unknown"),
        "duration_ms": _duration_ms(span.get("start_time"), span.get("end_time")),
        "payload_size_bytes": int(span.get("payload_size_bytes") or 0),
        "token_count": span.get("token_count"),
        "status": span.get("status", "unknown"),
        "error_summary": _safe_error_summary(span.get("error_summary")),
        "policy_decision": decision.get("action", "not_evaluated"),
        "redaction_markers": sorted(span.get("redaction_markers") or []),
    }


def _component_versions(trace: Dict[str, Any]) -> Dict[str, str]:
    language = str(trace.get("language") or "runtime")
    return {
        "agent_capsule_sdk": str(trace.get("sdk_version") or "unknown"),
        language: str(trace.get("runtime_version") or "unknown"),
        "agent_version": str((trace.get("agent") or {}).get("version") or "unknown"),
    }


def _policy_decisions(spans: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    decisions = []
    for span in spans:
        decision = span.get("policy_decision") or {}
        action = decision.get("action")
        if not action or action == "not_evaluated":
            continue
        decisions.append({
            "span_id": span.get("span_id", "unknown"),
            "action": action,
            "reason": _sanitize_text(decision.get("reason", "")),
        })
    return decisions


def _content_hashes(spans: Sequence[Dict[str, Any]], payload_index: Sequence[Dict[str, Any]]) -> List[str]:
    hashes: Set[str] = set()
    for span in spans:
        span_hash = span.get("content_hash")
        if span_hash:
            hashes.add(span_hash)
        error_summary = span.get("error_summary")
        if isinstance(error_summary, dict) and error_summary.get("stack_hash"):
            hashes.add(error_summary["stack_hash"])
    for payload in payload_index:
        payload_hash = payload.get("content_hash")
        if payload_hash:
            hashes.add(payload_hash)
    return sorted(hashes)


def _redaction_markers(spans: Sequence[Dict[str, Any]]) -> List[str]:
    markers: Set[str] = set()
    for span in spans:
        markers.update(span.get("redaction_markers") or [])
    return sorted(markers)


def _diagnostic_summary(spans: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    failure = _failure_span(spans)
    if failure is None:
        return {
            "status": "ok",
            "failure_span_id": None,
            "summary": "Run completed without error spans.",
        }

    error_summary = _safe_error_summary(failure.get("error_summary"))
    if error_summary:
        summary = "%s failed: %s" % (failure.get("component_name", "span"), error_summary)
    else:
        summary = "%s ended with status %s." % (
            failure.get("component_name", "span"),
            failure.get("status", "unknown"),
        )
    return {
        "status": failure.get("status", "unknown"),
        "failure_span_id": failure.get("span_id"),
        "summary": _sanitize_text(summary),
    }


def _failure_span(spans: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for status in ("error", "blocked", "approval_required"):
        for span in spans:
            if span.get("status") == status:
                return span
    return None


def _safe_error_summary(error_summary: Any) -> Optional[str]:
    if error_summary is None:
        return None
    if isinstance(error_summary, dict):
        error_type = _sanitize_text(str(error_summary.get("type") or "Error"))
        message = _sanitize_text(str(error_summary.get("message") or ""))
        if message:
            return "%s: %s" % (error_type, message)
        return error_type
    return _sanitize_text(str(error_summary))


def _safe_created_by(value: str) -> str:
    if scan_safe_trace({"created_by": value}):
        return "local-developer"
    return value or "local-developer"


def _sanitize_text(value: str) -> str:
    sanitized = value.replace("\n", " ").strip()
    for pattern in SENSITIVE_VALUE_PATTERNS:
        sanitized = pattern.sub("[redacted]", sanitized)
    if len(sanitized) > 240:
        sanitized_hash = content_hash(sanitized)
        sanitized = "%s [truncated:%s]" % (sanitized[:180], sanitized_hash)
    return sanitized


def _duration_ms(start_time: Any, end_time: Any) -> int:
    if not isinstance(start_time, str) or not isinstance(end_time, str):
        return 0
    try:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except ValueError:
        return 0
    return max(0, int((end - start).total_seconds() * 1000))


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

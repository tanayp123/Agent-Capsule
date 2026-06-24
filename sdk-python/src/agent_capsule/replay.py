import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .hashing import payload_size_bytes
from .safe_trace import scan_safe_trace
from .trace_store import EncryptedTraceStore


REPLAY_VERSION = 1
COMPARISON_VERSION = 1
REPLAY_MODES = {"structural", "mocked", "redacted", "approved_plaintext"}


class ReplayError(ValueError):
    pass


def replay_trace_from_store(
    store: EncryptedTraceStore,
    run_id: str,
    mode: str = "structural",
    approve_plaintext: bool = False,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    if mode not in REPLAY_MODES:
        raise ReplayError("unsupported replay mode: %s" % mode)
    if mode == "approved_plaintext" and not approve_plaintext:
        raise ReplayError("approved_plaintext replay requires explicit plaintext approval")

    trace = store.find_trace_by_run_id(run_id)
    if trace is None:
        raise ReplayError("trace not found for run_id: %s" % run_id)

    payload_index = _load_payload_index(store, trace["trace_id"])
    replay = build_replay(
        trace=trace,
        payload_index=payload_index,
        payload_reader=store.read_payload if mode == "approved_plaintext" else None,
        mode=mode,
        approve_plaintext=approve_plaintext,
        created_at=created_at,
    )
    findings = scan_safe_trace(replay)
    if findings:
        raise ReplayError("replay artifact scanner found plaintext risk: %s" % "; ".join(findings))
    return replay


def build_replay(
    trace: Dict[str, Any],
    payload_index: Sequence[Dict[str, Any]],
    mode: str = "structural",
    approve_plaintext: bool = False,
    payload_reader: Optional[Any] = None,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    if mode not in REPLAY_MODES:
        raise ReplayError("unsupported replay mode: %s" % mode)
    if mode == "approved_plaintext" and not approve_plaintext:
        raise ReplayError("approved_plaintext replay requires explicit plaintext approval")

    records_by_span = _records_by_span(payload_index)
    plaintext_count = 0
    replay_spans = []
    for span in trace.get("spans", []):
        records = records_by_span.get(span.get("span_id"), [])
        replay_span, used_plaintext = _replay_span(
            trace_id=trace["trace_id"],
            span=span,
            records=records,
            mode=mode,
            payload_reader=payload_reader,
        )
        plaintext_count += used_plaintext
        replay_spans.append(replay_span)

    replay = {
        "replay_version": REPLAY_VERSION,
        "source_trace_id": trace["trace_id"],
        "source_run_id": trace["run_id"],
        "created_at": created_at or _now(),
        "mode": mode,
        "payload_policy": {
            "raw_payloads_exported": False,
            "encrypted_payloads_decrypted": bool(mode == "approved_plaintext" and approve_plaintext),
            "plaintext_payloads_used": plaintext_count,
        },
        "workflow": {
            "span_count": len(replay_spans),
            "root_span_ids": [
                span["source_span_id"]
                for span in replay_spans
                if span.get("parent_span_id") is None
            ],
        },
        "destinations": _replay_destinations(trace.get("destinations", [])),
        "spans": replay_spans,
    }
    findings = scan_safe_trace(replay)
    if findings:
        raise ReplayError("replay artifact scanner found plaintext risk: %s" % "; ".join(findings))
    return replay


def compare_trace_to_replay(trace: Dict[str, Any], replay: Dict[str, Any]) -> Dict[str, Any]:
    source_spans = trace.get("spans", [])
    replay_spans = replay.get("spans", [])
    differences: List[Dict[str, Any]] = []

    source_structure = [_source_structure(span) for span in source_spans]
    replay_structure = [_replay_structure(span) for span in replay_spans]
    if source_structure != replay_structure:
        differences.append({
            "category": "span_structure",
            "message": "span structure changed",
            "expected": source_structure,
            "actual": replay_structure,
        })

    source_by_id = {span.get("span_id"): span for span in source_spans}
    replay_by_id = {span.get("source_span_id"): span for span in replay_spans}
    for span_id in sorted(set(source_by_id).union(replay_by_id)):
        source_span = source_by_id.get(span_id)
        replay_span = replay_by_id.get(span_id)
        if source_span is None or replay_span is None:
            continue
        differences.extend(_span_differences(source_span, replay_span))

    source_destinations = _destination_signature(trace.get("destinations", []))
    replay_destinations = _destination_signature(replay.get("destinations", []))
    if source_destinations != replay_destinations:
        differences.append({
            "category": "destination_changes",
            "message": "destination set changed",
            "expected": sorted(source_destinations),
            "actual": sorted(replay_destinations),
        })

    return {
        "comparison_version": COMPARISON_VERSION,
        "source_trace_id": trace.get("trace_id"),
        "candidate_replay_source_trace_id": replay.get("source_trace_id"),
        "status": "match" if not differences else "diverged",
        "summary": {
            "difference_count": len(differences),
            "span_count": len(source_spans),
        },
        "differences": differences,
    }


def _replay_span(
    trace_id: str,
    span: Dict[str, Any],
    records: Sequence[Dict[str, Any]],
    mode: str,
    payload_reader: Optional[Any],
) -> Tuple[Dict[str, Any], int]:
    decision = span.get("policy_decision") or {}
    replay_span = {
        "source_span_id": span.get("span_id"),
        "parent_span_id": span.get("parent_span_id"),
        "component_type": span.get("component_type"),
        "component_name": span.get("component_name"),
        "destination_id": span.get("destination_id"),
        "status": span.get("status"),
        "simulated_duration_ms": _duration_ms(span.get("start_time"), span.get("end_time")),
        "payload_size_bytes": span.get("payload_size_bytes", 0),
        "token_count": span.get("token_count"),
        "content_hash": span.get("content_hash"),
        "policy_decision_action": decision.get("action", "not_evaluated"),
        "policy_decision_reason": decision.get("reason", ""),
        "error_type": _error_type(span.get("error_summary")),
        "replay_action": _replay_action(span, records, mode),
        "payload_references": _payload_references(records),
    }

    plaintext_count = 0
    if mode == "mocked":
        replay_span["mocked_result"] = _mocked_result(span, records)
    elif mode == "redacted":
        replay_span["redacted_payloads"] = _redacted_payloads(records)
    elif mode == "approved_plaintext":
        verification, plaintext_count = _verify_plaintext_payloads(trace_id, records, payload_reader)
        replay_span["local_plaintext_verification"] = verification

    return replay_span, plaintext_count


def _replay_action(span: Dict[str, Any], records: Sequence[Dict[str, Any]], mode: str) -> str:
    component_type = span.get("component_type")
    if mode == "structural" or not records:
        return "structural_replay"
    if mode == "mocked" and component_type == "model_call":
        return "mocked_model_response"
    if mode == "mocked" and component_type == "tool_call":
        return "mocked_tool_result"
    if mode == "redacted":
        return "redacted_payload_replay"
    if mode == "approved_plaintext":
        return "approved_plaintext_local_replay"
    return "structural_replay"


def _mocked_result(span: Dict[str, Any], records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    result_record = _first_record(records, "result") or _first_record(records, "result_context")
    source_hash = result_record.get("content_hash") if result_record else span.get("content_hash")
    component_type = span.get("component_type")
    if component_type == "model_call":
        return {
            "kind": "model_response",
            "source_hash": source_hash,
            "token_count": span.get("token_count"),
            "mock_value": "[mocked]",
        }
    if component_type == "tool_call":
        return {
            "kind": "tool_result",
            "source_hash": source_hash,
            "mock_value": "[mocked]",
        }
    return {
        "kind": "span_result",
        "source_hash": source_hash,
        "mock_value": "[mocked]",
    }


def _redacted_payloads(records: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [
        {
            "payload_id": record.get("payload_id", ""),
            "kind": record.get("kind", ""),
            "content_hash": record.get("content_hash", ""),
            "replacement": "[redacted:%s]" % record.get("kind", "payload"),
        }
        for record in records
    ]


def _verify_plaintext_payloads(
    trace_id: str,
    records: Sequence[Dict[str, Any]],
    payload_reader: Optional[Any],
) -> Tuple[List[Dict[str, Any]], int]:
    if payload_reader is None:
        raise ReplayError("approved plaintext replay requires a payload reader")

    verification = []
    for record in records:
        payload_id = record.get("payload_id")
        payload = payload_reader(trace_id, payload_id)
        stored_hash = payload.get("content_hash")
        expected_hash = record.get("content_hash")
        verification.append({
            "payload_id": payload_id,
            "kind": record.get("kind", ""),
            "content_hash": expected_hash,
            "verified": stored_hash == expected_hash,
            "payload_size_bytes": payload_size_bytes(payload.get("payload")),
        })
    return verification, len(verification)


def _payload_references(records: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [
        {
            "payload_id": record.get("payload_id", ""),
            "kind": record.get("kind", ""),
            "content_hash": record.get("content_hash", ""),
            "mode": "hash_only",
        }
        for record in records
    ]


def _replay_destinations(destinations: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": destination.get("id"),
            "type": destination.get("type"),
            "domain": destination.get("domain"),
            "risk": destination.get("risk"),
            "declared_in_policy": destination.get("declared_in_policy", False),
            "observed_data_classes": sorted(destination.get("observed_data_classes") or []),
        }
        for destination in sorted(destinations, key=lambda item: item.get("id", ""))
    ]


def _span_differences(source_span: Dict[str, Any], replay_span: Dict[str, Any]) -> List[Dict[str, Any]]:
    differences = []
    span_id = source_span.get("span_id")
    checks = [
        ("timing", _duration_ms(source_span.get("start_time"), source_span.get("end_time")), replay_span.get("simulated_duration_ms")),
        ("token_counts", source_span.get("token_count"), replay_span.get("token_count")),
        ("policy_decision_changes", (source_span.get("policy_decision") or {}).get("action"), replay_span.get("policy_decision_action")),
        ("error_changes", _error_signature(source_span), _replay_error_signature(replay_span)),
    ]
    for category, expected, actual in checks:
        if expected != actual:
            differences.append({
                "category": category,
                "span_id": span_id,
                "message": "%s changed for span %s" % (category, span_id),
                "expected": expected,
                "actual": actual,
            })
    return differences


def _source_structure(span: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "span_id": span.get("span_id"),
        "parent_span_id": span.get("parent_span_id"),
        "component_type": span.get("component_type"),
        "component_name": span.get("component_name"),
        "destination_id": span.get("destination_id"),
    }


def _replay_structure(span: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "span_id": span.get("source_span_id"),
        "parent_span_id": span.get("parent_span_id"),
        "component_type": span.get("component_type"),
        "component_name": span.get("component_name"),
        "destination_id": span.get("destination_id"),
    }


def _destination_signature(destinations: Sequence[Dict[str, Any]]) -> Set[Tuple[Any, Any, Any]]:
    return {
        (
            destination.get("id"),
            destination.get("domain"),
            destination.get("risk"),
        )
        for destination in destinations
    }


def _error_signature(span: Dict[str, Any]) -> Tuple[Any, Any]:
    return span.get("status"), _error_type(span.get("error_summary"))


def _replay_error_signature(span: Dict[str, Any]) -> Tuple[Any, Any]:
    return span.get("status"), span.get("error_type")


def _error_type(error_summary: Any) -> Optional[str]:
    if isinstance(error_summary, dict):
        return error_summary.get("type")
    if isinstance(error_summary, str) and error_summary:
        return error_summary.split(":", 1)[0]
    return None


def _records_by_span(payload_index: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in payload_index:
        grouped.setdefault(record.get("span_id", ""), []).append(record)
    return {
        span_id: sorted(records, key=lambda item: (item.get("kind", ""), item.get("payload_id", "")))
        for span_id, records in grouped.items()
    }


def _first_record(records: Sequence[Dict[str, Any]], kind: str) -> Optional[Dict[str, Any]]:
    for record in records:
        if record.get("kind") == kind:
            return record
    return None


def _load_payload_index(store: EncryptedTraceStore, trace_id: str) -> List[Dict[str, Any]]:
    index_path = store.index_path(trace_id)
    if not index_path.exists():
        return []
    try:
        value = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return value if isinstance(value, list) else []


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

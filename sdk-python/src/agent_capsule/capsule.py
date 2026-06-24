import contextvars
import inspect
import os
import platform
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .classification import classify_payload
from .guard import transform_call_arguments
from .hashing import content_hash, payload_size_bytes
from .trace_store import EncryptedTraceStore
from policy_engine import evaluate_policy, load_policy_file

SDK_VERSION = "0.1.0"

_current_run = contextvars.ContextVar("agent_capsule_current_run", default=None)
_current_span_id = contextvars.ContextVar("agent_capsule_current_span_id", default=None)


ApprovalHandler = Callable[[Dict[str, Any]], bool]


class CapsuleGuardError(RuntimeError):
    pass


class PolicyViolationError(CapsuleGuardError):
    pass


class HumanApprovalRequired(CapsuleGuardError):
    pass


@dataclass
class Destination:
    id: str
    type: str
    domain: Optional[str]
    provider: str
    environment: str = "production"
    risk: str = "medium"
    declared_in_policy: bool = False
    allowed_data_classes: Optional[List[str]] = None
    observed_data_classes: Optional[List[str]] = None

    def to_trace_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "domain": self.domain,
            "provider": self.provider,
            "environment": self.environment,
            "risk": self.risk,
            "declared_in_policy": self.declared_in_policy,
            "allowed_data_classes": self.allowed_data_classes or [],
            "observed_data_classes": self.observed_data_classes or [],
        }


class Capsule:
    def __init__(
        self,
        mode: str,
        policy_path: Optional[str],
        trace_dir: Path,
        agent_name: str,
        agent_version: str,
        approval_handler: Optional[ApprovalHandler] = None,
    ) -> None:
        if mode not in ("observe", "guard", "confidential"):
            raise ValueError("unsupported mode: %s" % mode)

        self.mode = mode
        self.policy_path = policy_path
        self.trace_dir = trace_dir
        self.agent_name = agent_name
        self.agent_version = agent_version
        self.approval_handler = approval_handler
        self.trace_store = EncryptedTraceStore(trace_dir)
        self.policy = None
        self.policy_version = None
        self.warnings: List[str] = []
        self._load_policy()

    @classmethod
    def init(
        cls,
        mode: str = "observe",
        policy: Optional[str] = None,
        trace_dir: Optional[str] = None,
        agent_name: str = "agent",
        agent_version: str = "0.1.0",
        approval_handler: Optional[ApprovalHandler] = None,
    ) -> "Capsule":
        resolved_mode = os.environ.get("AGENT_CAPSULE_MODE", mode)
        resolved_policy = policy or os.environ.get("AGENT_CAPSULE_POLICY")
        resolved_trace_dir = Path(trace_dir or os.environ.get("AGENT_CAPSULE_TRACE_DIR", ".agent-capsule/traces"))
        return cls(
            mode=resolved_mode,
            policy_path=resolved_policy,
            trace_dir=resolved_trace_dir,
            agent_name=agent_name,
            agent_version=agent_version,
            approval_handler=approval_handler,
        )

    def run(self, name: str, run_id: Optional[str] = None) -> "Run":
        return Run(self, name=name, run_id=run_id)

    def current_run(self) -> "Run":
        run = _current_run.get()
        if run is None:
            raise RuntimeError("Agent Capsule operation requires an active run context")
        return run

    def model(
        self,
        component_name: str,
        destination: Destination,
        token_counter: Optional[Callable[[Any], int]] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._wrap_call(
            component_type="model_call",
            component_name=component_name,
            destination=destination,
            token_counter=token_counter,
        )

    def tool(
        self,
        component_name: str,
        destination: Destination,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._wrap_call(
            component_type="tool_call",
            component_name=component_name,
            destination=destination,
            token_counter=None,
        )

    def wrap_model_client(
        self,
        call: Callable[..., Any],
        component_name: str,
        destination: Destination,
        token_counter: Optional[Callable[[Any], int]] = None,
    ) -> Callable[..., Any]:
        return self.model(component_name, destination, token_counter=token_counter)(call)

    def wrap_tool(
        self,
        call: Callable[..., Any],
        component_name: str,
        destination: Destination,
    ) -> Callable[..., Any]:
        return self.tool(component_name, destination)(call)

    def _wrap_call(
        self,
        component_type: str,
        component_name: str,
        destination: Destination,
        token_counter: Optional[Callable[[Any], int]],
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(call: Callable[..., Any]) -> Callable[..., Any]:
            if inspect.iscoroutinefunction(call):
                async def async_wrapped(*args: Any, **kwargs: Any) -> Any:
                    run = self.current_run()
                    payload = {"args": args, "kwargs": kwargs}
                    with run.span(
                        component_type=component_type,
                        component_name=component_name,
                        payload=payload,
                        destination=destination,
                    ) as span:
                        guarded_args, guarded_kwargs = span.prepare_egress(args, kwargs)
                        result = await call(*guarded_args, **guarded_kwargs)
                        span.set_result(result, token_counter=token_counter)
                        return result

                async_wrapped.__name__ = getattr(call, "__name__", "async_wrapped")
                async_wrapped.__doc__ = getattr(call, "__doc__", None)
                return async_wrapped

            def wrapped(*args: Any, **kwargs: Any) -> Any:
                run = self.current_run()
                payload = {"args": args, "kwargs": kwargs}
                with run.span(
                    component_type=component_type,
                    component_name=component_name,
                    payload=payload,
                    destination=destination,
                ) as span:
                    guarded_args, guarded_kwargs = span.prepare_egress(args, kwargs)
                    result = call(*guarded_args, **guarded_kwargs)
                    span.set_result(result, token_counter=token_counter)
                    return result

            wrapped.__name__ = getattr(call, "__name__", "wrapped")
            wrapped.__doc__ = getattr(call, "__doc__", None)
            return wrapped

        return decorator

    def _load_policy(self) -> None:
        if not self.policy_path:
            self._warn_or_raise("policy not configured")
            return

        path = Path(self.policy_path)
        if not path.exists():
            self._warn_or_raise("policy file not found: %s" % self.policy_path)
            return

        try:
            self.policy = load_policy_file(path)
            self.policy_version = self.policy.get("version")
        except Exception as exc:
            self._warn_or_raise("policy could not be loaded: %s" % exc)

    def _warn_or_raise(self, message: str) -> None:
        if self.mode == "observe":
            self.warnings.append(message)
            return
        raise PolicyViolationError(message)


class Run:
    def __init__(self, capsule: Capsule, name: str, run_id: Optional[str] = None) -> None:
        self.capsule = capsule
        self.name = name
        self.run_id = run_id or _id("run")
        self.trace_id = _id("trc")
        self.spans: List[Dict[str, Any]] = []
        self.payloads: List[Dict[str, Any]] = []
        self.destinations: Dict[str, Destination] = {}
        self._token = None
        self._root_span: Optional[Span] = None
        self.trace_path: Optional[Path] = None

    def __enter__(self) -> "Run":
        self._token = _current_run.set(self)
        self._root_span = self.span("workflow", self.name)
        self._root_span.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        try:
            if self._root_span is not None:
                self._root_span.__exit__(exc_type, exc, tb)
            self.trace_path = self.write_trace()
        finally:
            if self._token is not None:
                _current_run.reset(self._token)
        return False

    async def __aenter__(self) -> "Run":
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return self.__exit__(exc_type, exc, tb)

    def span(
        self,
        component_type: str,
        component_name: str,
        payload: Any = None,
        destination: Optional[Destination] = None,
        token_count: Optional[int] = None,
        data_classes: Optional[Iterable[str]] = None,
    ) -> "Span":
        if destination is not None:
            self.register_destination(destination)
        return Span(
            run=self,
            component_type=component_type,
            component_name=component_name,
            payload=payload,
            destination=destination,
            token_count=token_count,
            explicit_data_classes=list(data_classes or []),
        )

    def register_destination(self, destination: Destination) -> None:
        existing = self.destinations.get(destination.id)
        if existing is None:
            self.destinations[destination.id] = destination
            return

        observed = set(existing.observed_data_classes or [])
        observed.update(destination.observed_data_classes or [])
        existing.observed_data_classes = sorted(observed)

    def record_output(self, output: Any) -> None:
        with self.span(
            component_type="workflow",
            component_name="record_output",
            payload=output,
            data_classes=["model_output"],
        ):
            pass

    def write_trace(self) -> Path:
        return self.capsule.trace_store.write_trace(self.to_trace_dict(), self.payloads)

    def to_trace_dict(self) -> Dict[str, Any]:
        return {
            "trace_schema_version": 1,
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "agent": {
                "name": self.capsule.agent_name,
                "version": self.capsule.agent_version,
            },
            "mode": self.capsule.mode,
            "language": "python",
            "runtime_version": platform.python_version(),
            "sdk_version": SDK_VERSION,
            "created_at": _now(),
            "spans": self.spans,
            "destinations": [
                destination.to_trace_dict()
                for destination in sorted(self.destinations.values(), key=lambda item: item.id)
            ],
        }


class Span:
    def __init__(
        self,
        run: Run,
        component_type: str,
        component_name: str,
        payload: Any,
        destination: Optional[Destination],
        token_count: Optional[int],
        explicit_data_classes: List[str],
    ) -> None:
        self.run = run
        self.span_id = _id("spn")
        self.parent_span_id = _current_span_id.get()
        self.component_type = component_type
        self.component_name = component_name
        self.payload = payload
        self.destination = destination
        self.token_count = token_count
        self.explicit_data_classes = explicit_data_classes
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None
        self.status = "ok"
        self.error_summary = None
        self._token = None
        self._payload_size_bytes = 0
        self._content_hash = None
        self._data_classes: List[str] = []
        self._redaction_markers: List[str] = []
        self._recorded_payload_kinds: List[str] = []
        self._policy_decision: Optional[Dict[str, Any]] = None

    def __enter__(self) -> "Span":
        self.start_time = _now()
        self._token = _current_span_id.set(self.span_id)
        self._apply_payload(self.payload)
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if exc is not None:
            if not isinstance(exc, CapsuleGuardError):
                self.status = "error"
            self.error_summary = _error_summary(exc, tb)
        self.end_time = _now()
        self._append_to_run()
        if self._token is not None:
            _current_span_id.reset(self._token)
        return False

    async def __aenter__(self) -> "Span":
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return self.__exit__(exc_type, exc, tb)

    def set_result(
        self,
        result: Any,
        token_counter: Optional[Callable[[Any], int]] = None,
    ) -> None:
        payload = {
            "input_hash": self._content_hash,
            "result": result,
        }
        self._apply_payload(payload, kind="result_context")
        self._record_payload(result, kind="result")
        result_classes, result_markers = classify_payload({"model_output": result})
        self._data_classes = sorted(set(self._data_classes).union(result_classes))
        self._redaction_markers = sorted(set(self._redaction_markers).union(result_markers))
        if token_counter is not None:
            self.token_count = token_counter(result)
        elif self.token_count is None and isinstance(result, str):
            self.token_count = len(result.split())

    def prepare_egress(self, args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        decision = self._ensure_policy_decision()
        action = decision["action"]
        if action == "warn":
            self.run.capsule.warnings.append(self._warning_message(decision))

        if self.run.capsule.mode == "observe":
            return args, kwargs

        if action == "block":
            self.status = "blocked"
            raise PolicyViolationError(self._violation_message(decision))

        if action == "require_approval":
            if not self._approval_granted(decision):
                self.status = "approval_required"
                raise HumanApprovalRequired(self._violation_message(decision))
            return args, kwargs

        if action in ("redact", "allow_fields"):
            if action == "redact" and self.status == "ok":
                self.status = "redacted"
            return transform_call_arguments(args, kwargs, action, decision["fields"])

        return args, kwargs

    def _apply_payload(self, payload: Any, kind: str = "input") -> None:
        if payload is None:
            if self._content_hash is None:
                self._content_hash = None
                self._payload_size_bytes = 0
            return

        payload_classes, markers = classify_payload(payload)
        payload_classes = sorted(set(payload_classes).union(self.explicit_data_classes))
        self._data_classes = sorted(set(self._data_classes).union(payload_classes))
        self._redaction_markers = sorted(set(self._redaction_markers).union(markers))
        self._payload_size_bytes = payload_size_bytes(payload)
        self._content_hash = content_hash(payload)
        self._record_payload(payload, kind=kind)

        if self.destination is not None:
            observed = set(self.destination.observed_data_classes or [])
            observed.update(payload_classes)
            self.destination.observed_data_classes = sorted(observed)
            self.run.register_destination(self.destination)

    def _record_payload(self, payload: Any, kind: str) -> None:
        if payload is None or kind in self._recorded_payload_kinds:
            return
        self.run.payloads.append(
            {
                "span_id": self.span_id,
                "kind": kind,
                "payload": payload,
            }
        )
        self._recorded_payload_kinds.append(kind)

    def _append_to_run(self) -> None:
        policy_decision = self._ensure_policy_decision()
        self.run.spans.append(
            {
                "span_id": self.span_id,
                "parent_span_id": self.parent_span_id,
                "component_type": self.component_type,
                "component_name": self.component_name,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "status": self.status,
                "payload_size_bytes": self._payload_size_bytes,
                "token_count": self.token_count,
                "content_hash": self._content_hash,
                "data_classes": self._data_classes,
                "destination_id": self.destination.id if self.destination else None,
                "policy_decision": policy_decision,
                "error_summary": self.error_summary,
                "redaction_markers": self._redaction_markers,
            }
        )

    def _ensure_policy_decision(self) -> Dict[str, Any]:
        if self._policy_decision is None:
            self._policy_decision = self._evaluate_policy_decision()
            self._apply_policy_status(self._policy_decision)
        return self._policy_decision

    def _evaluate_policy_decision(self) -> Dict[str, Any]:
        if self.component_type == "workflow" and self.destination is None:
            return {
                "action": "not_evaluated",
                "reason": "workflow span",
                "policy_version": self.run.capsule.policy_version,
                "fields": [],
            }

        if self.run.capsule.policy is None:
            return {
                "action": "warn" if self.destination else "not_evaluated",
                "reason": "observe mode policy not loaded" if self.destination else "no destination",
                "policy_version": self.run.capsule.policy_version,
                "fields": self._data_classes,
            }

        if self.destination is not None:
            destination_policy = self.run.capsule.policy.get("destinations", {}).get(self.destination.id)
            self.destination.declared_in_policy = destination_policy is not None
            if destination_policy is not None:
                self.destination.allowed_data_classes = destination_policy.get("allowed_data", [])
                self.destination.risk = destination_policy.get("risk", self.destination.risk)
                self.destination.domain = destination_policy.get("domain", self.destination.domain)

        decision = evaluate_policy(
            self.run.capsule.policy,
            destination_id=self.destination.id if self.destination else None,
            destination_risk=self.destination.risk if self.destination else "low",
            data_classes=self._data_classes,
            fields=self._data_classes,
            mode=self.run.capsule.mode,
        )
        return decision.to_trace_dict()

    def _apply_policy_status(self, decision: Dict[str, Any]) -> None:
        if decision["action"] == "redact" and self.status == "ok":
            self.status = "redacted"
        if decision["action"] == "require_approval" and self.status == "ok" and self.run.capsule.mode != "observe":
            self.status = "approval_required"
        if decision["action"] == "block" and self.status == "ok" and self.run.capsule.mode != "observe":
            self.status = "blocked"

    def _approval_granted(self, decision: Dict[str, Any]) -> bool:
        handler = self.run.capsule.approval_handler
        if handler is None:
            return False
        request = {
            "run_id": self.run.run_id,
            "trace_id": self.run.trace_id,
            "span_id": self.span_id,
            "component_type": self.component_type,
            "component_name": self.component_name,
            "destination_id": self.destination.id if self.destination else None,
            "decision_action": decision["action"],
            "reason": decision["reason"],
            "fields": list(decision["fields"]),
            "policy_version": decision["policy_version"],
            "content_hash": self._content_hash,
            "payload_size_bytes": self._payload_size_bytes,
        }
        try:
            approved = bool(handler(request))
        except Exception:
            return False
        if approved and self.status == "approval_required":
            self.status = "ok"
        return approved

    def _violation_message(self, decision: Dict[str, Any]) -> str:
        return (
            "Agent Capsule policy %s for component %s destination %s: %s; fields=%s"
            % (
                decision["action"],
                self.component_name,
                self.destination.id if self.destination else "none",
                decision["reason"],
                ",".join(decision["fields"]),
            )
        )

    def _warning_message(self, decision: Dict[str, Any]) -> str:
        return "Agent Capsule policy warning for destination %s: %s; fields=%s" % (
            self.destination.id if self.destination else "none",
            decision["reason"],
            ",".join(decision["fields"]),
        )


def _id(prefix: str) -> str:
    return "%s_%s" % (prefix, uuid.uuid4().hex)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error_summary(exc: BaseException, tb: Any) -> Dict[str, str]:
    stack = "".join(traceback.format_exception(type(exc), exc, tb))
    from .hashing import content_hash as hash_content

    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "stack_hash": hash_content(stack),
    }

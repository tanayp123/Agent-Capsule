import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


VALID_DESTINATION_TYPES = {
    "model_provider",
    "external_tool",
    "internal_service",
    "database",
    "retrieval_system",
    "secrets_provider",
    "human_approval",
}

VALID_RISKS = ("low", "medium", "high", "critical")
RISK_RANK = {risk: index for index, risk in enumerate(VALID_RISKS)}
DEFAULT_ACTIONS = {
    "undeclared_high_risk_egress": {"block", "warn"},
    "undeclared_destination": {"block", "warn"},
    "secrets": {"block", "require_approval"},
}

DATA_CLASS_RISK = {
    "account_id": "medium",
    "account_notes": "high",
    "address": "high",
    "claimant_name": "high",
    "customer_identifier": "high",
    "document_text": "high",
    "email": "high",
    "incident_description": "medium",
    "medical_information": "high",
    "model_output": "high",
    "policy_number": "medium",
    "prompt_content": "high",
    "secrets": "critical",
    "support_tier": "low",
    "tool_payload": "high",
    "user_identifier": "high",
}


class PolicyEngineError(ValueError):
    pass


@dataclass(frozen=True)
class PolicyDecision:
    action: str
    reason: str
    policy_version: Optional[int]
    fields: Tuple[str, ...]

    def to_trace_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "policy_version": self.policy_version,
            "fields": list(self.fields),
        }


def load_policy_file(path: Path) -> Dict[str, Any]:
    policy_path = Path(path)
    try:
        policy = parse_policy_text(policy_path.read_text(encoding="utf-8"), suffix=policy_path.suffix)
    except json.JSONDecodeError as exc:
        raise PolicyEngineError("policy JSON is malformed") from exc
    except PolicyEngineError:
        raise
    except Exception as exc:
        raise PolicyEngineError("policy could not be parsed: %s" % exc) from exc

    errors = validate_policy_object(policy)
    if errors:
        raise PolicyEngineError("invalid policy: %s" % "; ".join(errors))
    return normalize_policy(policy)


def load_trace_file(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PolicyEngineError("trace JSON is malformed") from exc


def parse_policy_text(text: str, suffix: str = "") -> Dict[str, Any]:
    if suffix.lower() == ".json" or text.lstrip().startswith("{"):
        value = json.loads(text)
        if not isinstance(value, dict):
            raise PolicyEngineError("policy must be a JSON object")
        return value
    return _parse_simple_yaml(text)


def validate_policy_object(policy: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not isinstance(policy, dict):
        return ["policy must be an object"]

    version = policy.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        errors.append("version must be an integer greater than 0")

    agent = policy.get("agent")
    if not isinstance(agent, dict):
        errors.append("agent must be an object")
    else:
        for key in ("name", "owner"):
            if not isinstance(agent.get(key), str) or not agent.get(key):
                errors.append("agent.%s must be a non-empty string" % key)

    destinations = policy.get("destinations")
    if not isinstance(destinations, dict):
        errors.append("destinations must be an object")
    else:
        for destination_id, destination in destinations.items():
            errors.extend(_validate_destination(destination_id, destination))

    defaults = policy.get("defaults")
    if not isinstance(defaults, dict):
        errors.append("defaults must be an object")
    else:
        for key, allowed_actions in DEFAULT_ACTIONS.items():
            action = defaults.get(key)
            if action not in allowed_actions:
                errors.append("defaults.%s must be one of %s" % (key, ", ".join(sorted(allowed_actions))))

    return errors


def normalize_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
    destinations = {}
    for destination_id, destination in policy.get("destinations", {}).items():
        destinations[destination_id] = {
            "type": destination["type"],
            "domain": destination.get("domain"),
            "risk": destination["risk"],
            "allowed_data": _sorted_unique(destination.get("allowed_data", [])),
            "redact": _sorted_unique(destination.get("redact", [])),
            "require_approval": _sorted_unique(destination.get("require_approval", [])),
        }
    return {
        "version": policy["version"],
        "agent": {
            "name": policy["agent"]["name"],
            "owner": policy["agent"]["owner"],
        },
        "destinations": destinations,
        "defaults": {
            "undeclared_high_risk_egress": policy["defaults"]["undeclared_high_risk_egress"],
            "undeclared_destination": policy["defaults"]["undeclared_destination"],
            "secrets": policy["defaults"]["secrets"],
        },
    }


def evaluate_policy(
    policy: Dict[str, Any],
    destination_id: Optional[str],
    destination_risk: str,
    data_classes: Iterable[str],
    fields: Optional[Iterable[str]] = None,
    mode: str = "guard",
) -> PolicyDecision:
    normalized = normalize_policy(policy)
    data = _sorted_unique(data_classes)
    observed_fields = _sorted_unique(fields if fields is not None else data)
    observed_tokens = set(data).union(observed_fields)
    output_fields = tuple(observed_fields or data)
    policy_version = normalized.get("version")

    if not destination_id:
        return PolicyDecision("not_evaluated", "no destination", policy_version, tuple())

    if "secrets" in observed_tokens:
        decision = PolicyDecision(
            normalized["defaults"]["secrets"],
            "secrets default rule matched",
            policy_version,
            output_fields,
        )
        return _apply_mode(decision, mode)

    destination = normalized["destinations"].get(destination_id)
    egress_risk = classify_egress_risk(destination_risk, data)

    if destination is None:
        if _is_high_or_critical(egress_risk):
            decision = PolicyDecision(
                normalized["defaults"]["undeclared_high_risk_egress"],
                "undeclared high-risk egress",
                policy_version,
                output_fields,
            )
            return _apply_mode(decision, mode)
        decision = PolicyDecision(
            normalized["defaults"]["undeclared_destination"],
            "undeclared destination",
            policy_version,
            output_fields,
        )
        return _apply_mode(decision, mode)

    approval_fields = _matched_fields(observed_fields, data, destination["require_approval"])
    if approval_fields:
        return PolicyDecision(
            "require_approval",
            "destination approval rule matched",
            policy_version,
            tuple(approval_fields),
        )

    redaction_fields = _matched_fields(observed_fields, data, destination["redact"])
    if redaction_fields:
        return PolicyDecision(
            "redact",
            "destination redaction rule matched",
            policy_version,
            tuple(redaction_fields),
        )

    allowed = set(destination["allowed_data"])
    if allowed and not observed_tokens.issubset(allowed):
        allowed_fields = [field for field in observed_fields if field in allowed]
        if not allowed_fields:
            allowed_fields = [data_class for data_class in data if data_class in allowed]
        return PolicyDecision(
            "allow_fields",
            "destination allowlist excluded fields",
            policy_version,
            tuple(_sorted_unique(allowed_fields)),
        )

    return PolicyDecision(
        "allow",
        "destination declared and data allowed",
        policy_version,
        output_fields,
    )


def generate_privacy_map(trace: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_policy(policy)
    destination_registry = {
        destination["id"]: dict(destination)
        for destination in trace.get("destinations", [])
        if isinstance(destination, dict) and destination.get("id")
    }
    span_groups: Dict[str, List[Dict[str, Any]]] = {}
    for span in trace.get("spans", []):
        destination_id = span.get("destination_id")
        if destination_id:
            span_groups.setdefault(destination_id, []).append(span)

    destinations = []
    findings = []
    suggestions = []

    for destination_id in sorted(span_groups):
        spans = span_groups[destination_id]
        registry_entry = destination_registry.get(destination_id, {})
        declared = destination_id in normalized["destinations"]
        destination_policy = normalized["destinations"].get(destination_id, {})
        destination_risk = registry_entry.get("risk") or destination_policy.get("risk") or "medium"
        observed_data = _sorted_unique(_flatten(span.get("data_classes", []) for span in spans))
        egress_risk = classify_egress_risk(destination_risk, observed_data)
        decisions = [
            evaluate_policy(
                normalized,
                destination_id=destination_id,
                destination_risk=destination_risk,
                data_classes=span.get("data_classes", []),
                fields=span.get("data_classes", []),
                mode=trace.get("mode", "guard"),
            )
            for span in spans
        ]
        actions = _sorted_unique(decision.action for decision in decisions)
        destination_findings = []

        if not declared:
            destination_findings.append("undeclared_destination")
            findings.append(_finding(
                kind="undeclared_destination",
                severity="warning",
                destination_id=destination_id,
                risk=egress_risk,
                data_classes=observed_data,
                message="Destination %s is not declared in policy" % destination_id,
            ))
            if _is_high_or_critical(egress_risk):
                destination_findings.append("undeclared_high_risk_egress")
                findings.append(_finding(
                    kind="undeclared_high_risk_egress",
                    severity="error",
                    destination_id=destination_id,
                    risk=egress_risk,
                    data_classes=observed_data,
                    message="Undeclared high-risk egress remains for destination %s" % destination_id,
                ))
            suggestions.extend(suggest_policy_actions(
                destination_id=destination_id,
                destination_type=registry_entry.get("type", "external_tool"),
                domain=registry_entry.get("domain"),
                risk=destination_risk,
                observed_data_classes=observed_data,
            ))

        for decision in decisions:
            if decision.action in ("allow_fields", "redact", "require_approval", "block", "warn"):
                destination_findings.append(decision.action)

        destinations.append({
            "id": destination_id,
            "type": registry_entry.get("type") or destination_policy.get("type"),
            "domain": registry_entry.get("domain") or destination_policy.get("domain"),
            "provider": registry_entry.get("provider"),
            "environment": registry_entry.get("environment", "production"),
            "declared_in_policy": declared,
            "destination_risk": destination_risk,
            "egress_risk": egress_risk,
            "observed_data_classes": observed_data,
            "allowed_data_classes": destination_policy.get("allowed_data", []),
            "span_count": len(spans),
            "actions": actions,
            "findings": _sorted_unique(destination_findings),
        })

    return {
        "trace_id": trace.get("trace_id"),
        "run_id": trace.get("run_id"),
        "policy_version": normalized.get("version"),
        "destinations": destinations,
        "findings": sorted(findings, key=lambda item: (item["destination_id"], item["kind"])),
        "policy_suggestions": suggestions,
    }


def suggest_policy_actions(
    destination_id: str,
    destination_type: str,
    domain: Optional[str],
    risk: str,
    observed_data_classes: Sequence[str],
) -> List[Dict[str, Any]]:
    observed = _sorted_unique(observed_data_classes)
    base = {
        "type": destination_type,
        "domain": domain,
        "risk": risk,
    }
    return [
        {
            "destination_id": destination_id,
            "action": "allow",
            "description": "Declare the destination and allow the observed data classes.",
            "policy_patch": {destination_id: dict(base, allowed_data=observed, redact=[], require_approval=[])},
        },
        {
            "destination_id": destination_id,
            "action": "allow_fields",
            "description": "Declare the destination and choose a smaller allowed_data list from observed classes.",
            "policy_patch": {destination_id: dict(base, allowed_data=observed, redact=[], require_approval=[])},
        },
        {
            "destination_id": destination_id,
            "action": "redact",
            "description": "Declare the destination but redact the observed data classes before egress.",
            "policy_patch": {destination_id: dict(base, allowed_data=[], redact=observed, require_approval=[])},
        },
        {
            "destination_id": destination_id,
            "action": "require_approval",
            "description": "Declare the destination and require human approval for the observed data classes.",
            "policy_patch": {destination_id: dict(base, allowed_data=[], redact=[], require_approval=observed)},
        },
        {
            "destination_id": destination_id,
            "action": "block",
            "description": "Keep the destination undeclared or remove the tool call from the workflow.",
            "policy_patch": {},
        },
    ]


def classify_data_risk(data_classes: Iterable[str]) -> str:
    risk = "low"
    for data_class in data_classes:
        candidate = DATA_CLASS_RISK.get(data_class, "medium")
        risk = _max_risk(risk, candidate)
    return risk


def classify_egress_risk(destination_risk: str, data_classes: Iterable[str]) -> str:
    return _max_risk(_normalize_risk(destination_risk), classify_data_risk(data_classes))


def _validate_destination(destination_id: str, destination: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(destination_id, str) or not destination_id:
        errors.append("destination id must be a non-empty string")
    if not isinstance(destination, dict):
        return ["destinations.%s must be an object" % destination_id]

    destination_type = destination.get("type")
    if destination_type not in VALID_DESTINATION_TYPES:
        errors.append("destinations.%s.type must be one of %s" % (
            destination_id,
            ", ".join(sorted(VALID_DESTINATION_TYPES)),
        ))

    if destination.get("domain") is not None and not isinstance(destination.get("domain"), str):
        errors.append("destinations.%s.domain must be a string or null" % destination_id)

    if destination.get("risk") not in VALID_RISKS:
        errors.append("destinations.%s.risk must be one of %s" % (destination_id, ", ".join(VALID_RISKS)))

    for key in ("allowed_data", "redact", "require_approval"):
        if not isinstance(destination.get(key), list) or not all(isinstance(item, str) for item in destination.get(key, [])):
            errors.append("destinations.%s.%s must be a string list" % (destination_id, key))

    return errors


def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    parsed: Dict[str, Any] = {}
    stack: List[Tuple[int, Any]] = [(-1, parsed)]
    pending_key: Optional[str] = None
    pending_parent: Optional[Dict[str, Any]] = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if stripped.startswith("- "):
            if pending_key is None:
                raise PolicyEngineError("YAML list item without parent key")
            parent = pending_parent
            if not isinstance(parent, dict):
                raise PolicyEngineError("YAML list parent must be a mapping")
            current = parent.get(pending_key)
            if current is None or isinstance(current, dict):
                current = []
                parent[pending_key] = current
            if not isinstance(current, list):
                raise PolicyEngineError("YAML key %s cannot contain both list and map values" % pending_key)
            current.append(_parse_scalar(stripped[2:].strip()))
            continue

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if not isinstance(parent, dict):
            raise PolicyEngineError("YAML nested mapping cannot be placed under a list")

        if ":" not in stripped:
            raise PolicyEngineError("YAML line is missing ':'")
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise PolicyEngineError("YAML key cannot be empty")

        if value == "":
            child: Dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
            pending_key = key
            pending_parent = parent
        else:
            parent[key] = _parse_scalar(value)
            pending_key = None
            pending_parent = None

    if not isinstance(parsed, dict):
        raise PolicyEngineError("YAML policy must be a mapping")
    return parsed


def _parse_scalar(value: str) -> Any:
    if value in ("{}", "[]"):
        return {} if value == "{}" else []
    if value in ("null", "None", "~"):
        return None
    if value in ("true", "false"):
        return value == "true"
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def _matched_fields(fields: Sequence[str], data_classes: Sequence[str], rules: Sequence[str]) -> List[str]:
    rule_set = set(rules)
    matched = [field for field in fields if field in rule_set]
    matched.extend(data_class for data_class in data_classes if data_class in rule_set)
    return _sorted_unique(matched)


def _finding(
    kind: str,
    severity: str,
    destination_id: str,
    risk: str,
    data_classes: Sequence[str],
    message: str,
) -> Dict[str, Any]:
    return {
        "kind": kind,
        "severity": severity,
        "destination_id": destination_id,
        "risk": risk,
        "data_classes": list(data_classes),
        "message": message,
    }


def _apply_mode(decision: PolicyDecision, mode: str) -> PolicyDecision:
    if mode == "observe" and decision.action == "block":
        return PolicyDecision(
            "warn",
            "observe_only: %s" % decision.reason,
            decision.policy_version,
            decision.fields,
        )
    return decision


def _normalize_risk(risk: str) -> str:
    return risk if risk in RISK_RANK else "medium"


def _is_high_or_critical(risk: str) -> bool:
    return RISK_RANK[_normalize_risk(risk)] >= RISK_RANK["high"]


def _max_risk(left: str, right: str) -> str:
    left = _normalize_risk(left)
    right = _normalize_risk(right)
    return left if RISK_RANK[left] >= RISK_RANK[right] else right


def _sorted_unique(values: Iterable[Any]) -> List[str]:
    return sorted({str(value) for value in values if value is not None})


def _flatten(values: Iterable[Iterable[Any]]) -> List[Any]:
    flattened: List[Any] = []
    for value in values:
        flattened.extend(value)
    return flattened

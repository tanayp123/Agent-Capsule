import dataclasses
import hashlib
import json
from typing import Any


def normalize_payload(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return normalize_payload(dataclasses.asdict(value))

    if hasattr(value, "model_dump") and callable(value.model_dump):
        return normalize_payload(value.model_dump())

    if hasattr(value, "dict") and callable(value.dict):
        return normalize_payload(value.dict())

    if isinstance(value, dict):
        return {str(key): normalize_payload(value[key]) for key in sorted(value)}

    if isinstance(value, (list, tuple)):
        return [normalize_payload(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return repr(value)


def canonical_json(value: Any) -> str:
    return json.dumps(
        normalize_payload(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def payload_size_bytes(value: Any) -> int:
    return len(canonical_json(value).encode("utf-8"))


def content_hash(value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return "sha256:%s" % digest


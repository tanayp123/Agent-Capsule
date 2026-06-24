import dataclasses
from typing import Any, Dict, Iterable, List, Set, Tuple


FIELD_NAME_DATA_CLASSES = {
    "account_id": "account_id",
    "account_notes": "account_notes",
    "address": "address",
    "api_key": "secrets",
    "claimant_name": "claimant_name",
    "customer_id": "customer_identifier",
    "customer_identifier": "customer_identifier",
    "document": "document_text",
    "document_text": "document_text",
    "email": "email",
    "incident_description": "incident_description",
    "medical_details": "medical_information",
    "medical_information": "medical_information",
    "model_output": "model_output",
    "notes": "account_notes",
    "policy_number": "policy_number",
    "prompt": "prompt_content",
    "prompt_content": "prompt_content",
    "secret": "secrets",
    "support_tier": "support_tier",
    "tool_payload": "tool_payload",
    "user_id": "user_identifier",
    "user_identifier": "user_identifier",
}

SENSITIVE_DATA_CLASSES = {
    "account_notes",
    "address",
    "claimant_name",
    "customer_identifier",
    "document_text",
    "email",
    "incident_description",
    "medical_information",
    "model_output",
    "policy_number",
    "prompt_content",
    "secrets",
    "tool_payload",
    "user_identifier",
}


class ClassifiedField:
    def __init__(self, value: Any, data_classes: Iterable[str]):
        self.value = value
        self.data_classes = tuple(data_classes)


def classified_field(value: Any, data_classes: Iterable[str]) -> ClassifiedField:
    return ClassifiedField(value, data_classes)


def classify_payload(payload: Any) -> Tuple[List[str], List[str]]:
    data_classes = _collect_data_classes(payload)
    markers = []
    for data_class in sorted(data_classes):
        prefix = "redacted" if data_class == "secrets" else "hashed"
        if data_class in SENSITIVE_DATA_CLASSES:
            markers.append("%s:%s" % (prefix, data_class))
    return sorted(data_classes), markers


def _collect_data_classes(value: Any) -> Set[str]:
    classes = set()

    if isinstance(value, ClassifiedField):
        classes.update(value.data_classes)
        classes.update(_collect_data_classes(value.value))
        return classes

    if dataclasses.is_dataclass(value):
        for field in dataclasses.fields(value):
            field_value = getattr(value, field.name)
            classes.update(_classes_for_field(field.name, field.metadata))
            classes.update(_collect_data_classes(field_value))
        return classes

    pydantic_fields = _pydantic_field_metadata(value)
    if pydantic_fields is not None:
        for field_name, metadata in pydantic_fields.items():
            field_value = getattr(value, field_name, None)
            classes.update(_classes_for_field(field_name, metadata))
            classes.update(_collect_data_classes(field_value))
        return classes

    if isinstance(value, dict):
        for key, item in value.items():
            classes.update(_classes_for_field(str(key), {}))
            classes.update(_collect_data_classes(item))
        return classes

    if isinstance(value, (list, tuple, set)):
        for item in value:
            classes.update(_collect_data_classes(item))
        return classes

    return classes


def _classes_for_field(name: str, metadata: Any) -> Set[str]:
    classes = set()
    normalized_name = name.lower()
    if normalized_name in FIELD_NAME_DATA_CLASSES:
        classes.add(FIELD_NAME_DATA_CLASSES[normalized_name])

    if isinstance(metadata, dict):
        explicit = metadata.get("agent_capsule_data_classes") or metadata.get("data_classes")
        if explicit:
            classes.update(_as_list(explicit))

    return classes


def _as_list(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _pydantic_field_metadata(value: Any) -> Any:
    model_fields = getattr(value, "model_fields", None)
    if isinstance(model_fields, dict):
        return {
            name: _metadata_from_pydantic_field(field)
            for name, field in model_fields.items()
        }

    legacy_fields = getattr(value, "__fields__", None)
    if isinstance(legacy_fields, dict):
        return {
            name: _metadata_from_pydantic_field(field)
            for name, field in legacy_fields.items()
        }

    return None


def _metadata_from_pydantic_field(field: Any) -> Dict[str, Any]:
    json_schema_extra = getattr(field, "json_schema_extra", None)
    if isinstance(json_schema_extra, dict):
        return json_schema_extra

    field_info = getattr(field, "field_info", None)
    extra = getattr(field_info, "extra", None)
    if isinstance(extra, dict):
        return extra

    return {}


import dataclasses
from typing import Any, Dict, Iterable, Mapping, Set, Tuple

from .classification import ClassifiedField, FIELD_NAME_DATA_CLASSES


REDACTION_PREFIX = "[redacted:"


def transform_call_arguments(
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    action: str,
    fields: Iterable[str],
) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
    selected = {str(field) for field in fields}
    if action == "redact":
        return (
            tuple(redact_payload(arg, selected) for arg in args),
            {key: redact_payload(value, selected, key) for key, value in kwargs.items()},
        )
    if action == "allow_fields":
        return (
            tuple(filter_allowed_payload(arg, selected) for arg in args),
            {key: filter_allowed_payload(value, selected, key) for key, value in kwargs.items()},
        )
    return args, kwargs


def redact_payload(value: Any, fields: Set[str], field_name: str = "") -> Any:
    if isinstance(value, ClassifiedField):
        if _matches_classes(set(value.data_classes), fields):
            return _marker(_first_match(set(value.data_classes), fields))
        return redact_payload(value.value, fields, field_name)

    field_classes = _classes_for_name(field_name)
    if field_name and _matches_classes(field_classes.union({field_name}), fields):
        return _marker(_first_match(field_classes.union({field_name}), fields))

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        updates = {
            field.name: redact_payload(getattr(value, field.name), fields, field.name)
            for field in dataclasses.fields(value)
        }
        try:
            return dataclasses.replace(value, **updates)
        except TypeError:
            return updates

    if isinstance(value, Mapping):
        return {
            key: redact_payload(item, fields, str(key))
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [redact_payload(item, fields) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_payload(item, fields) for item in value)
    if isinstance(value, set):
        return {redact_payload(item, fields) for item in value}

    return value


def filter_allowed_payload(value: Any, fields: Set[str], field_name: str = "") -> Any:
    if isinstance(value, ClassifiedField):
        if _matches_classes(set(value.data_classes), fields):
            return filter_allowed_payload(value.value, fields, field_name)
        return _marker("allow_fields")

    field_classes = _classes_for_name(field_name)
    if field_name and field_classes and not _matches_classes(field_classes.union({field_name}), fields):
        return _marker("allow_fields")

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        updates = {
            field.name: filter_allowed_payload(getattr(value, field.name), fields, field.name)
            for field in dataclasses.fields(value)
        }
        try:
            return dataclasses.replace(value, **updates)
        except TypeError:
            return updates

    if isinstance(value, Mapping):
        filtered = {}
        for key, item in value.items():
            key_text = str(key)
            key_classes = _classes_for_name(key_text)
            if key_classes and not _matches_classes(key_classes.union({key_text}), fields):
                continue
            filtered[key] = filter_allowed_payload(item, fields, key_text)
        return filtered

    if isinstance(value, list):
        return [filter_allowed_payload(item, fields) for item in value]
    if isinstance(value, tuple):
        return tuple(filter_allowed_payload(item, fields) for item in value)
    if isinstance(value, set):
        return {filter_allowed_payload(item, fields) for item in value}

    return value


def _classes_for_name(name: str) -> Set[str]:
    data_class = FIELD_NAME_DATA_CLASSES.get(name.lower()) if name else None
    return {data_class} if data_class else set()


def _matches_classes(classes: Set[str], fields: Set[str]) -> bool:
    return bool(classes.intersection(fields))


def _first_match(classes: Set[str], fields: Set[str]) -> str:
    matches = sorted(classes.intersection(fields))
    return matches[0] if matches else "field"


def _marker(name: str) -> str:
    return "%s%s]" % (REDACTION_PREFIX, name)

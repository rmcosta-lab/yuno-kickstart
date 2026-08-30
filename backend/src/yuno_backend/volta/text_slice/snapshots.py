"""Safe JSON codecs for immutable provider-neutral replay projections."""

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from importlib import import_module
from typing import Any
from uuid import UUID

from yuno_backend.volta.errors import InvalidDomainValue

__all__ = ["decode_snapshot", "encode_snapshot"]

_TYPE = "__volta_type__"


def encode_snapshot(value: object) -> dict[str, object]:
    encoded = _encode(value)
    if not isinstance(encoded, dict):
        raise InvalidDomainValue("result_snapshot", "object_required")
    return encoded


def decode_snapshot(snapshot: Mapping[str, object], expected_type: type[Any]) -> Any:
    value = _decode(dict(snapshot))
    if not isinstance(value, expected_type):
        raise InvalidDomainValue("result_snapshot", "unexpected_result_kind")
    return value


def _encode(value: object) -> object:
    if isinstance(value, Enum):
        return {_TYPE: "enum", "class": _class_name(type(value)), "value": value.value}
    if isinstance(value, UUID):
        return {_TYPE: "uuid", "value": str(value)}
    if isinstance(value, datetime):
        return {_TYPE: "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {_TYPE: "date", "value": value.isoformat()}
    if isinstance(value, Decimal):
        return {_TYPE: "decimal", "value": format(value, "f")}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            _TYPE: "dataclass",
            "class": _class_name(type(value)),
            "fields": {item.name: _encode(getattr(value, item.name)) for item in fields(value)},
        }
    if isinstance(value, tuple):
        return {_TYPE: "tuple", "items": [_encode(item) for item in value]}
    if isinstance(value, Mapping):
        return {
            _TYPE: "mapping",
            "items": [[_encode(key), _encode(item)] for key, item in value.items()],
        }
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise InvalidDomainValue("result_snapshot", "unsupported_value")


def _decode(value: object) -> object:
    if isinstance(value, (list, tuple)):
        return [_decode(item) for item in value]
    if not isinstance(value, Mapping) or _TYPE not in value:
        return value
    value = dict(value)
    kind = value[_TYPE]
    if kind == "uuid":
        return UUID(_string(value, "value"))
    if kind == "datetime":
        return datetime.fromisoformat(_string(value, "value"))
    if kind == "date":
        return date.fromisoformat(_string(value, "value"))
    if kind == "decimal":
        return Decimal(_string(value, "value"))
    if kind == "tuple":
        items = value.get("items")
        if not isinstance(items, (list, tuple)):
            raise InvalidDomainValue("result_snapshot", "invalid_tuple")
        return tuple(_decode(item) for item in items)
    if kind == "mapping":
        items = value.get("items")
        if not isinstance(items, (list, tuple)):
            raise InvalidDomainValue("result_snapshot", "invalid_mapping")
        return {_decode_pair(item)[0]: _decode_pair(item)[1] for item in items}
    cls = _load_class(_string(value, "class"))
    if kind == "enum":
        return cls(value.get("value"))
    if kind == "dataclass":
        raw_fields = value.get("fields")
        if not isinstance(raw_fields, Mapping) or not is_dataclass(cls):
            raise InvalidDomainValue("result_snapshot", "invalid_dataclass")
        return cls(**{name: _decode(item) for name, item in raw_fields.items()})
    raise InvalidDomainValue("result_snapshot", "unsupported_type")


def _decode_pair(value: object) -> tuple[object, object]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise InvalidDomainValue("result_snapshot", "invalid_mapping_item")
    return _decode(value[0]), _decode(value[1])


def _class_name(cls: type[object]) -> str:
    module = cls.__module__
    if not module.startswith("yuno_backend.volta."):
        raise InvalidDomainValue("result_snapshot", "unsafe_class")
    return f"{module}:{cls.__qualname__}"


def _load_class(name: str) -> type[Any]:
    module_name, separator, qualname = name.partition(":")
    if not separator or not module_name.startswith("yuno_backend.volta."):
        raise InvalidDomainValue("result_snapshot", "unsafe_class")
    value: object = import_module(module_name)
    for part in qualname.split("."):
        value = getattr(value, part, None)
    if not isinstance(value, type):
        raise InvalidDomainValue("result_snapshot", "unknown_class")
    return value


def _string(value: Mapping[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise InvalidDomainValue("result_snapshot", "invalid_scalar")
    return item

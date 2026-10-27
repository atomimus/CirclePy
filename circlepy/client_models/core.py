"""Small payload helpers for the Postman-defined legacy Admin API."""

from collections.abc import Mapping
from copy import deepcopy
from urllib.parse import quote


UNSET = object()


def segment(value):
    return quote(str(value), safe="")


def copy_payload(payload):
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return deepcopy(dict(payload))


def query_payload(payload, community_id):
    """Encode v1 query arrays with brackets; explicit empty/null is a blank value.

    Query strings cannot represent JSON null. Forwarding a blank value does not
    promise that Circle accepts it or interprets it as a clearing instruction.
    """
    data = copy_payload(payload)
    data.setdefault("community_id", community_id)
    result = {}

    def add(key, value):
        if isinstance(value, Mapping):
            if not value:
                result[key] = ""
            for child, item in value.items():
                add(f"{key}[{child}]", item)
        elif isinstance(value, (list, tuple)):
            key = key if key.endswith("[]") else key + "[]"
            result[key] = [scalar(item) for item in value] if value else ""
        else:
            result[key] = scalar(value)

    def scalar(value):
        if value is None:
            return ""
        if isinstance(value, bool):
            return str(value).lower()
        return value

    for key, value in data.items():
        # An unconfigured client should not manufacture a blank community ID.
        if key == "community_id" and value is None and key not in payload:
            continue
        add(key, value)
    return result

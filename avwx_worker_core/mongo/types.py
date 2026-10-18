"""Pydantic field types for MongoDB documents."""

from __future__ import annotations

from typing import Annotated, Any

from bson import ObjectId
from pydantic import PlainSerializer, PlainValidator, SerializationInfo, WithJsonSchema


def _to_object_id(value: Any) -> ObjectId:
    """Accept an ObjectId or its 24-character hex string."""
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    msg = f"Not a valid ObjectId: {value!r}"
    raise ValueError(msg)


def _serialize(value: ObjectId, info: SerializationInfo) -> ObjectId | str:
    """Native in Python mode, so documents written back to Mongo keep the real type."""
    return str(value) if info.mode_is_json() else value


#: A real `bson.ObjectId` in Python and in documents written back to Mongo, and a hex
#: string in JSON. Keeping the native type matters: a stringified id silently matches
#: nothing when used in a query against `_id`.
type ObjectIdField = Annotated[
    ObjectId,
    PlainValidator(_to_object_id),
    PlainSerializer(_serialize, return_type=Any),
    WithJsonSchema({"type": "string", "pattern": "^[0-9a-f]{24}$"}),
]

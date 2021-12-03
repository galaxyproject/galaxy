"""This module contains utility functions shared across the api package."""
from typing import Any, Dict, Optional

from fastapi import Query

from galaxy.schema import SerializationParams
from galaxy.schema.schema import UpdateDatasetPermissionsPayload

SerializationViewQueryParam: Optional[str] = Query(
    None,
    title='View',
    description='View to be passed to the serializer',
)

SerializationKeysQueryParam: Optional[str] = Query(
    None,
    title='Keys',
    description='Comma-separated list of keys to be passed to the serializer',
)

SerializationDefaultViewQueryParam: Optional[str] = Query(
    None,
    title='Default View',
    description='The item view that will be used in case no particular view was specified.',
)


def parse_serialization_params(
    view: Optional[str] = None,
    keys: Optional[str] = None,
    default_view: Optional[str] = None,
    **_,  # Additional params are ignored
) -> SerializationParams:
    key_list = None
    if keys:
        key_list = keys.split(',')
    return SerializationParams(view=view, keys=key_list, default_view=default_view)


def query_serialization_params(
    view: Optional[str] = SerializationViewQueryParam,
    keys: Optional[str] = SerializationKeysQueryParam,
    default_view: Optional[str] = SerializationDefaultViewQueryParam,
) -> SerializationParams:
    return parse_serialization_params(view=view, keys=keys, default_view=default_view)


def get_update_permission_payload(payload: Dict[str, Any]) -> UpdateDatasetPermissionsPayload:
    """Coverts the generic payload dictionary into a UpdateDatasetPermissionsPayload model with custom parsing.
    This is an attempt on supporting multiple aliases for the permissions params."""
    # There are several allowed names for the same role list parameter, i.e.: `access`, `access_ids`, `access_ids[]`
    # The `access_ids[]` name is not pydantic friendly, so this will be modelled as an alias but we can only set one alias
    # TODO: Maybe we should choose only one way/naming and deprecate the others?
    payload["access_ids"] = payload.get("access_ids[]") or payload.get("access")
    payload["manage_ids"] = payload.get("manage_ids[]") or payload.get("manage")
    payload["modify_ids"] = payload.get("modify_ids[]") or payload.get("modify")
    update_payload = UpdateDatasetPermissionsPayload(**payload)
    return update_payload

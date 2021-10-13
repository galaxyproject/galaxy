"""This module contains utility functions shared across the api package."""
from typing import Optional

from fastapi import Query

from galaxy.schema import SerializationParams

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

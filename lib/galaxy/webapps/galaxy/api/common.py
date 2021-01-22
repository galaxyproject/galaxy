"""This module contains utility functions shared across the api package."""
from typing import Optional

from fastapi import Query

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


def parse_serialization_params(view, keys, default_view):
    key_list = None
    if keys:
        key_list = keys.split(',')
    return dict(view=view, keys=key_list, default_view=default_view)

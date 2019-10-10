"""
The Galaxy web application framework
"""

from .framework import url_for
from .framework.base import httpexceptions
# TODO: Make _future_* the default.
from .framework.decorators import (
    _future_expose_api,
    _future_expose_api_anonymous,
    _future_expose_api_anonymous_and_sessionless,
    _future_expose_api_raw,
    _future_expose_api_raw_anonymous,
    _future_expose_api_raw_anonymous_and_sessionless,
    error,
    expose,
    expose_api,
    expose_api_anonymous,
    expose_api_raw,
    expose_api_raw_anonymous,
    json,
    json_pretty,
    require_admin,
    require_login
)

__all__ = ('url_for', 'error', 'expose', 'json', 'json_pretty',
           'require_admin', 'require_login', 'expose_api', 'expose_api_anonymous',
           'expose_api_raw', 'expose_api_raw_anonymous', '_future_expose_api',
           '_future_expose_api_anonymous', '_future_expose_api_raw',
           '_future_expose_api_raw_anonymous',
           '_future_expose_api_anonymous_and_sessionless',
           '_future_expose_api_raw_anonymous_and_sessionless', 'form',
           'FormBuilder', 'httpexceptions')

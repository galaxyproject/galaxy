"""
The Galaxy web application framework
"""

from framework import url_for
from framework.decorators import error
from framework.decorators import expose
from framework.decorators import json
from framework.decorators import json_pretty
from framework.decorators import require_login
from framework.decorators import require_admin
from framework.decorators import expose_api
from framework.decorators import expose_api_anonymous
from framework.decorators import expose_api_raw
from framework.decorators import expose_api_raw_anonymous

# TODO: Drop and make these the default.
from framework.decorators import _future_expose_api
from framework.decorators import _future_expose_api_anonymous
from framework.decorators import _future_expose_api_raw
from framework.decorators import _future_expose_api_raw_anonymous
from framework.decorators import _future_expose_api_anonymous_and_sessionless
from framework.decorators import _future_expose_api_raw_anonymous_and_sessionless

from framework.formbuilder import form
from framework.formbuilder import FormBuilder

from framework.base import httpexceptions

__all__ = ['url_for', 'error', 'expose', 'json', 'json_pretty',
           'require_admin', 'require_login', 'expose_api', 'expose_api_anonymous',
           'expose_api_raw', 'expose_api_raw_anonymous', '_future_expose_api',
           '_future_expose_api_anonymous', '_future_expose_api_raw',
           '_future_expose_api_raw_anonymous',
           '_future_expose_api_anonymous_and_sessionless',
           '_future_expose_api_raw_anonymous_and_sessionless', 'form',
           'FormBuilder', 'httpexceptions']

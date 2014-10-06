"""
raven.middleware
~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010-2012 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""

import galaxy.eggs; galaxy.eggs.require( "raven" )

from raven import Client
from raven.utils.wsgi import get_current_url, get_headers, \
  get_environ

class Sentry(object):
    """
    A WSGI middleware which will attempt to capture any
    uncaught exceptions and send them to Sentry.
    """
    def __init__(self, application, dsn):
        self.application = application
        self.client = Client( dsn )

    def __call__(self, environ, start_response):
        try:
            iterable = self.application(environ, start_response)
        except Exception:
            self.handle_exception(environ)
            raise

        try:
            for event in iterable:
                yield event
        except Exception:
            self.handle_exception(environ)
            raise
        finally:
            # wsgi spec requires iterable to call close if it exists
            # see http://blog.dscpl.com.au/2012/10/obligations-for-calling-close-on.html
            if iterable and hasattr(iterable, 'close') and callable(iterable.close):
                try:
                    iterable.close()
                except Exception:
                    self.handle_exception(environ)

    def handle_exception(self, environ):
        event_id = self.client.captureException(
            data={
                'sentry.interfaces.Http': {
                    'method': environ.get('REQUEST_METHOD'),
                    'url': get_current_url(environ, strip_querystring=True),
                    'query_string': environ.get('QUERY_STRING'),
                    # TODO
                    # 'data': environ.get('wsgi.input'),
                    'headers': dict(get_headers(environ)),
                    'env': dict(get_environ(environ)),
                }
            },
            # Galaxy: add request id from environment if available
            extra={
                'request_id': environ.get( 'request_id', 'Unknown' )
            }
        )
        # Galaxy: store event_id in environment so we can show it to the user
        environ['sentry_event_id'] = event_id[0]

        return event_id

"""
raven.middleware
~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010-2012 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""

try:
    from raven import Client
    from raven.utils.wsgi import get_current_url, get_headers, get_environ
except:
    Client = None

from galaxy.util.postfork import register_postfork_function


RAVEN_IMPORT_MESSAGE = ('The Python raven package is required to use this '
                        'feature, please install it')


class Sentry(object):
    """
    A WSGI middleware which will attempt to capture any
    uncaught exceptions and send them to Sentry.
    """
    def __init__(self, application, dsn):
        assert Client is not None, RAVEN_IMPORT_MESSAGE
        self.application = application
        self.client = None

        def postfork_sentry_client():
            self.client = Client( dsn )

        register_postfork_function(postfork_sentry_client)

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
        headers = dict(get_headers(environ))
        # Authorization header for REMOTE_USER sites consists of a base64() of
        # their plaintext password. It is a security issue for this password to
        # be exposed to a third party system which may or may not be under
        # control of the same administrators as the local Authentication
        # system. E.g. university LDAP systems.
        if 'Authorization' in headers:
            # Redact so the administrator knows that a value is indeed present.
            headers['Authorization'] = 'redacted'
        # Passing cookies allows for impersonation of users (depending on
        # remote service) and can be considered a security risk as well. For
        # multiple services running alongside Galaxy on the same host, this
        # could allow a sentry user with access to logs to impersonate a user
        # on another service. In the case of services like Jupyter, this can be
        # a serious concern as that would allow for terminal access. Furthermore,
        # very little debugging information can be gained as a result of having
        # access to all of the users cookies (including Galaxy cookies)
        if 'Cookie' in headers:
            headers['Cookie'] = 'redacted'
        event_id = self.client.captureException(
            data={
                'sentry.interfaces.Http': {
                    'method': environ.get('REQUEST_METHOD'),
                    'url': get_current_url(environ, strip_querystring=True),
                    'query_string': environ.get('QUERY_STRING'),
                    # TODO
                    # 'data': environ.get('wsgi.input'),
                    'headers': headers,
                    'env': dict(get_environ(environ)),
                }
            },
            # Galaxy: add request id from environment if available
            extra={
                'request_id': environ.get( 'request_id', 'Unknown' )
            }
        )
        # Galaxy: store event_id in environment so we can show it to the user
        environ['sentry_event_id'] = event_id

        return event_id

"""The module describes the ``sentry`` error plugin plugin."""
import logging

from galaxy import web
from galaxy.util import string_as_bool, unicodify
from . import ErrorPlugin

log = logging.getLogger(__name__)

ERROR_TEMPLATE = u"""Galaxy Job Error: {tool_id} v{tool_version}

Command Line:
{command_line}

Stderr:
{stderr}

Stdout:
{stdout}

The user provided the following information:
{message}"""


class SentryPlugin(ErrorPlugin):
    """Send error report to Sentry.
    """
    plugin_type = "sentry"

    def __init__(self, **kwargs):
        self.app = kwargs['app']
        self.redact_user_details_in_bugreport = self.app.config.redact_user_details_in_bugreport
        self.verbose = string_as_bool(kwargs.get('verbose', False))
        self.user_submission = string_as_bool(kwargs.get('user_submission', False))
        self.custom_dsn = kwargs.get('custom_dsn', None)
        self.sentry = None
        # Use the built in one by default
        if hasattr(self.app, 'sentry_client'):
            self.sentry = self.app.sentry_client

        # if they've set a custom one, override.
        if self.custom_dsn:
            import raven
            self.sentry = raven.Client(self.custom_dsn, transport=raven.transport.HTTPTransport)

    def submit_report(self, dataset, job, tool, **kwargs):
        """Submit the error report to sentry
        """
        if self.sentry:
            user = job.get_user()
            extra = {
                'info': job.info,
                'id': job.id,
                'command_line': unicodify(job.command_line),
                'destination_id': unicodify(job.destination_id),
                'stderr': unicodify(job.stderr),
                'traceback': unicodify(job.traceback),
                'exit_code': job.exit_code,
                'stdout': unicodify(job.stdout),
                'handler': unicodify(job.handler),
                'tool_id': unicodify(job.tool_id),
                'tool_version': unicodify(job.tool_version),
                'tool_xml': unicodify(tool.config_file) if tool else None
            }
            if self.redact_user_details_in_bugreport:
                extra['email'] = 'redacted'
            else:
                if 'email' in kwargs:
                    extra['email'] = unicodify(kwargs['email'])

            # User submitted message
            extra['message'] = unicodify(kwargs.get('message', ''))

            # Construct the error message to send to sentry. The first line
            # will be the issue title, everything after that becomes the
            # "message"
            error_message = ERROR_TEMPLATE.format(**extra)

            # Update context with user information in a sentry-specific manner
            context = {}

            # Getting the url allows us to link to the dataset info page in case
            # anything is missing from this report.
            try:
                url = web.url_for(controller="dataset",
                                  action="show_params",
                                  dataset_id=self.app.security.encode_id(dataset.id),
                                  qualified=True)
            except AttributeError:
                # The above does not work when handlers are separate from the web handlers
                url = None

            if self.redact_user_details_in_bugreport:
                if user:
                    # Opauqe identifier
                    context['user'] = {
                        'id': user.id
                    }
            else:
                if user:
                    # User information here also places email links + allows seeing
                    # a list of affected users in the tags/filtering.
                    context['user'] = {
                        'name': user.username,
                        'email': user.email,
                    }

            context['request'] = {'url': url}

            self.sentry_client.context.merge(context)

            # Send the message, using message because
            response = self.sentry_client.capture(
                'raven.events.Message',
                tags={
                    'tool_id': job.tool_id,
                    'tool_version': job.tool_version,
                },
                extra=extra,
                message=unicodify(error_message),
            )
            return ('Submitted bug report to Sentry. Your guru meditation number is %s' % response, 'success')


__all__ = ('SentryPlugin', )

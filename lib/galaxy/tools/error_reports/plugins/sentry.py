"""The module describes the ``sentry`` error plugin plugin."""
import logging

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

from galaxy import web
from galaxy.util import string_as_bool
from . import ErrorPlugin

log = logging.getLogger(__name__)

SENTRY_SDK_IMPORT_MESSAGE = "The Python sentry-sdk package is required to use this feature, please install it"
ERROR_TEMPLATE = """Galaxy Job Error: {tool_id} v{tool_version}

Command Line:
{command_line}

Stderr:
{stderr}

Stdout:
{stdout}

The user provided the following information:
{message}"""


class SentryPlugin(ErrorPlugin):
    """Send error report to Sentry."""

    plugin_type = "sentry"

    def __init__(self, **kwargs):
        self.app = kwargs["app"]
        self.redact_user_details_in_bugreport = self.app.config.redact_user_details_in_bugreport
        self.verbose = string_as_bool(kwargs.get("verbose", False))
        self.user_submission = string_as_bool(kwargs.get("user_submission", False))
        assert sentry_sdk, SENTRY_SDK_IMPORT_MESSAGE

    def submit_report(self, dataset, job, tool, **kwargs):
        """Submit the error report to sentry"""
        extra = {
            "info": job.info,
            "id": job.id,
            "command_line": job.command_line,
            "destination_id": job.destination_id,
            "stderr": job.stderr,
            "traceback": job.traceback,
            "exit_code": job.exit_code,
            "stdout": job.stdout,
            "handler": job.handler,
            "tool_id": job.tool_id,
            "tool_version": job.tool_version,
            "tool_xml": tool.config_file if tool else None,
        }
        if self.redact_user_details_in_bugreport:
            extra["email"] = "redacted"
        else:
            if "email" in kwargs:
                extra["email"] = kwargs["email"]

        # User submitted message
        extra["message"] = kwargs.get("message", "")

        # Construct the error message to send to sentry. The first line
        # will be the issue title, everything after that becomes the
        # "message"
        error_message = ERROR_TEMPLATE.format(**extra)

        # Update context with user information in a sentry-specific manner
        context = {}

        # Getting the url allows us to link to the dataset info page in case
        # anything is missing from this report.
        try:
            url = web.url_for(
                controller="dataset",
                action="show_params",
                dataset_id=self.app.security.encode_id(dataset.id),
                qualified=True,
            )
        except AttributeError:
            # The above does not work when handlers are separate from the web handlers
            url = None

        user = job.get_user()
        if self.redact_user_details_in_bugreport:
            if user:
                # Opaque identifier
                context["user"] = {"id": user.id}
        else:
            if user:
                # User information here also places email links + allows seeing
                # a list of affected users in the tags/filtering.
                context["user"] = {
                    "name": user.username,
                    "email": user.email,
                }

        context["request"] = {"url": url}

        for key, value in context.items():
            sentry_sdk.set_context(key, value)
        sentry_sdk.set_context("job", extra)
        sentry_sdk.set_tag("tool_id", job.tool_id)
        sentry_sdk.set_tag("tool_version", job.tool_version)

        # Send the message, using message because
        response = sentry_sdk.capture_message(error_message)
        return (f"Submitted bug report to Sentry. Your guru meditation number is {response}", "success")


__all__ = ("SentryPlugin",)

"""The module describes the ``sentry`` error plugin."""

import logging
from typing import Dict

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

from galaxy.util import string_as_bool
from . import ErrorPlugin

log = logging.getLogger(__name__)

SENTRY_SDK_IMPORT_MESSAGE = "The Python sentry-sdk package is required to use this feature, please install it"
ERROR_TEMPLATE = "Galaxy Job Error: {tool_name}"


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
        """Submit the error report to Sentry."""
        tool_name = (
            job.tool_id
            if not job.tool_id.endswith(f"/{job.tool_version}")
            else job.tool_id[: -len(job.tool_version) - 1]
        )  # strip the tool's version from its long id

        # Add contexts to the report.
        contexts: Dict[str, dict] = {}

        # - "job" context
        contexts["job"] = {
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

        # - "feedback" context
        # The User Feedback API https://docs.sentry.io/api/projects/submit-user-feedback/ would be a better approach for
        # this.
        if "message" in kwargs:
            contexts["feedback"] = {
                "message": kwargs["message"],
            }

        for name, context in contexts.items():
            sentry_sdk.set_context(name, context)

        # Add user information to the report.
        user = job.get_user()
        sentry_user = {
            "id": user.id if user else None,
        }
        if user and not self.redact_user_details_in_bugreport:
            sentry_user.update(
                {
                    "username": user.username,
                    "email": user.email,
                }
            )
        sentry_sdk.set_user(sentry_user)

        # Add tags to the report.
        tags = {
            "tool": job.tool_id,
            "tool.name": tool_name,
            "tool.version": job.tool_version,
            "feedback": "yes" if "message" in kwargs else "no",
        }
        for name, value in tags.items():
            sentry_sdk.set_tag(name, value)

        # Construct the error message to send to sentry. The first line
        # will be the issue title, everything after that becomes the
        # "message".
        error_message = ERROR_TEMPLATE.format(
            tool_name=tool_name,
        )

        # Send the report as an error.
        sentry_sdk.set_level("error")

        # Send the report.
        response = sentry_sdk.capture_message(error_message)

        return f"Submitted bug report to Sentry. Your guru meditation number is {response}", "success"


__all__ = ("SentryPlugin",)

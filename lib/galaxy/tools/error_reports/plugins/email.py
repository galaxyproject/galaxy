"""The module describes the ``email`` error plugin."""

import logging

from galaxy.tools.errors import EmailErrorReporter
from galaxy.util import (
    string_as_bool,
    unicodify,
)
from galaxy.workflow.errors import WorkflowEmailErrorReporter
from . import ErrorPlugin

log = logging.getLogger(__name__)


class EmailPlugin(ErrorPlugin):
    """Send error report as an email"""

    plugin_type = "email"

    def __init__(self, **kwargs):
        self.app = kwargs["app"]
        self.redact_user_details_in_bugreport = self.app.config.redact_user_details_in_bugreport
        self.verbose = string_as_bool(kwargs.get("verbose", True))
        self.user_submission = string_as_bool(kwargs.get("user_submission", True))

    def submit_report(self, dataset, job, tool, **kwargs):
        """Send report as an email"""
        try:
            error_reporter = EmailErrorReporter(dataset.id, self.app)
            error_reporter.send_report(
                user=job.get_user(),
                email=kwargs.get("email", None),
                message=kwargs.get("message", None),
                redact_user_details_in_bugreport=self.redact_user_details_in_bugreport,
            )
            return ("Your error report has been sent", "success")
        except Exception as e:
            msg = f"An error occurred sending the report by email: {unicodify(e)}"
            log.exception(msg)
            return (msg, "danger")

    def submit_invocation_report(self, invocation, user, **kwargs):
        """Send report for a workflow invocation as an email"""
        try:
            error_reporter = WorkflowEmailErrorReporter(invocation, self.app)
            error_reporter.send_report(
                user=user,
                email=kwargs.get("email", None),
                message=kwargs.get("message", None),
                redact_user_details_in_bugreport=self.redact_user_details_in_bugreport,
            )
            return ("Your workflow error report has been sent", "success")
        except Exception as e:
            msg = f"An error occurred sending the workflow report by email: {unicodify(e)}"
            log.exception(msg)
            return (msg, "danger")


__all__ = ("EmailPlugin",)

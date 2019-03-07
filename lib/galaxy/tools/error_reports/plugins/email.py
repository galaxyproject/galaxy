"""The module describes the ``email`` error plugin."""
from __future__ import absolute_import

import logging

from galaxy.tools.errors import EmailErrorReporter
from galaxy.util import string_as_bool
from . import ErrorPlugin

log = logging.getLogger(__name__)


class EmailPlugin(ErrorPlugin):
    """Send error report as an email
    """
    plugin_type = "email"

    def __init__(self, **kwargs):
        self.app = kwargs['app']
        self.redact_user_details_in_bugreport = self.app.config.redact_user_details_in_bugreport
        self.verbose = string_as_bool(kwargs.get('verbose', True))
        self.user_submission = string_as_bool(kwargs.get('user_submission', True))

    def submit_report(self, dataset, job, tool, **kwargs):
        """Send report as an email
        """
        try:
            error_reporter = EmailErrorReporter(dataset.id, self.app)
            error_reporter.send_report(user=job.get_user(), email=kwargs.get('email', None), message=kwargs.get('message', None), redact_user_details_in_bugreport=self.redact_user_details_in_bugreport)
            return ("Your error report has been sent", "success")
        except Exception as e:
            return ("An error occurred sending the report by email: %s" % str(e), "danger")


__all__ = ('EmailPlugin', )

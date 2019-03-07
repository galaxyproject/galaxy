"""The module describes the ``json`` error plugin."""
from __future__ import absolute_import

import json
import logging
import os
import tempfile

from galaxy.util import string_as_bool
from . import ErrorPlugin

log = logging.getLogger(__name__)


class JsonPlugin(ErrorPlugin):
    """Write error report to a JSON file.
    """
    plugin_type = "json"

    def __init__(self, **kwargs):
        self.app = kwargs['app']
        self.verbose = string_as_bool(kwargs.get('verbose', False))
        self.redact_user_details_in_bugreport = self.app.config.redact_user_details_in_bugreport
        self.user_submission = string_as_bool(kwargs.get('user_submission', False))
        self.report_directory = kwargs.get("directory", tempfile.gettempdir())
        if not os.path.exists(self.report_directory):
            os.makedirs(self.report_directory)

    def submit_report(self, dataset, job, tool, **kwargs):
        """Write the report to a json file.
        """
        path = os.path.join(self.report_directory, str(dataset.id))
        with open(path, 'w') as handle:
            data = {
                'info' : job.info,
                'id' : job.id,
                'command_line' : job.command_line,
                'destination_id': job.destination_id,
                'stderr' : job.stderr,
                'traceback': job.traceback,
                'exit_code': job.exit_code,
                'stdout': job.stdout,
                'handler': job.handler,
                'tool_version': job.tool_version,
                'tool_xml': str(tool.config_file) if tool else None
            }
            if self.redact_user_details_in_bugreport:
                data['user'] = {
                    'id': job.get_user().id
                }
            else:
                data['user'] = job.get_user().to_dict()
                if 'email' in kwargs:
                    data['email'] = kwargs['email']

            if 'message' in kwargs:
                data['message'] = kwargs['message']

            json.dump(data, handle, indent=2)
        return ('Wrote error report to %s' % path, 'success')


__all__ = ('JsonPlugin', )

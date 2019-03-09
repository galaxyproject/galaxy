"""This module defines the common functions for error reporting for Galaxy jobs towards Git applications (e.g. Github/GitLab).
"""

from __future__ import absolute_import

import logging
import sys
import requests
import six
if sys.version_info[0] < 3:
    import urllib as urllib
    import urlparse as urlparse
else:
    import urllib.parse as urllib
    urlparse = urllib
from abc import (
    ABCMeta,
    abstractmethod
)

from galaxy.tools.errors import EmailErrorReporter
from galaxy.util import string_as_bool, unicodify
from . import ErrorPlugin

log = logging.getLogger(__name__)

@six.add_metaclass(ABCMeta)
class BaseGitPlugin(ErrorPlugin):
    """Base definition to send error reports to a Git repository provider
    """
    issue_cache = {}
    ts_urls = {}
    ts_repo_cache = {}
    git_project_cache = {}

    def _determine_ts_url(self, tool):
        if tool.tool_shed not in self.ts_urls:
            ts_url_request = requests.get('http://' + str(tool.tool_shed))
            self.ts_urls[tool.tool_shed] = ts_url_request.url
        return self.ts_urls[tool.tool_shed]

    def _get_gitrepo_from_ts(self, job, ts_url):
        if job.tool_id not in self.ts_repo_cache:
            ts_repo_request_data = requests.get(ts_url + "/api/repositories?tool_ids=" + str(job.tool_id)).json()

            for changeset, repoinfo in ts_repo_request_data.items():
                if isinstance(repoinfo, dict):
                    self.ts_repo_cache[job.tool_id] = repoinfo.get('repository', {}).get('remote_repository_url', None)
        return self.ts_repo_cache[job.tool_id]

    def _get_issue_cache_key(self, job, ts_repourl):
        return job.tool_id if ts_repourl else "default"

    def _generate_error_message(self, dataset, job, kwargs):
        # We'll re-use the email error reporter's template since most Git providers supports HTML
        error_reporter = EmailErrorReporter(dataset.id, self.app)
        error_reporter.create_report(job.get_user(), email=kwargs.get('email', None),
                                     message=kwargs.get('message', None),
                                     redact_user_details_in_bugreport=self.redact_user_details_in_bugreport)
        # Return the HTML report
        return error_reporter.html_report

    def _generate_error_title(self, job):
        tool_kw = {'tool_id': unicodify(job.tool_id), 'tool_version': unicodify(job.tool_version)}
        return u"""Galaxy Job Error: {tool_id} v{tool_version}""".format(**tool_kw)

    @abstractmethod
    def _create_issue(self, error_message, error_title, gl_project, issue_cache_key):
        raise NotImplementedError("Method _create_issue is required")

    @abstractmethod
    def _append_issue(self, error_message, error_title, gitlab_urlencodedpath, issue_cache_key):
        raise NotImplementedError("Method _append_issue is required")

    @abstractmethod
    def _fill_issue_cache(self, git_project, issue_cache_key):
        raise NotImplementedError("Method _fill_issue_cache is required")

"""This module defines the common functions for error reporting for Galaxy jobs towards Git applications (e.g. Github/GitLab)."""

import logging
from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import Dict

from galaxy.tools.errors import EmailErrorReporter
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    requests,
    unicodify,
)
from . import ErrorPlugin

log = logging.getLogger(__name__)


class BaseGitPlugin(ErrorPlugin, metaclass=ABCMeta):
    """Base definition to send error reports to a Git repository provider"""

    issue_cache: Dict[str, Dict] = {}
    ts_urls: Dict[str, str] = {}
    ts_repo_cache: Dict[str, Dict] = {}
    git_project_cache: Dict[str, Dict] = {}
    label_cache: Dict[str, Dict] = {}
    git_username_id_cache: Dict[str, str] = {}

    # Git variables
    git_default_repo_owner = False
    git_default_repo_name = False
    git_default_repo_only = True

    def _determine_ts_url(self, tool):
        if not tool.tool_shed or self.git_default_repo_only:
            return None
        try:
            if tool.tool_shed not in self.ts_urls:
                ts_url_request = requests.get(f"http://{tool.tool_shed}", timeout=DEFAULT_SOCKET_TIMEOUT)
                self.ts_urls[tool.tool_shed] = ts_url_request.url
            return self.ts_urls[tool.tool_shed]
        except Exception:
            return None

    def _get_gitrepo_from_ts(self, job, ts_url):
        if not ts_url or self.git_default_repo_only:
            return None
        try:
            if job.tool_id not in self.ts_repo_cache:
                ts_repo_request_data = requests.get(
                    f"{ts_url}/api/repositories?tool_ids={str(job.tool_id)}", timeout=DEFAULT_SOCKET_TIMEOUT
                ).json()

                for repoinfo in ts_repo_request_data.values():
                    if isinstance(repoinfo, dict):
                        self.ts_repo_cache[job.tool_id] = repoinfo.get("repository", {}).get(
                            "remote_repository_url", None
                        )
            return self.ts_repo_cache[job.tool_id]
        except Exception:
            return None

    def _get_issue_cache_key(self, job, ts_repourl):
        return job.tool_id if ts_repourl else "default"

    def _generate_error_message(self, dataset, job, kwargs):
        # We'll re-use the email error reporter's template since most Git providers supports HTML
        error_reporter = EmailErrorReporter(dataset.id, self.app)
        error_reporter.create_report(
            job.get_user(),
            email=kwargs.get("email", None),
            message=kwargs.get("message", None),
            redact_user_details_in_bugreport=self.redact_user_details_in_bugreport,
        )
        # Return the HTML report
        return error_reporter.html_report

    def _generate_error_title(self, job):
        tool_kw = {"tool_id": unicodify(job.tool_id), "tool_version": unicodify(job.tool_version)}
        return """Galaxy Job Error: {tool_id} v{tool_version}""".format(**tool_kw)

    @abstractmethod
    def _create_issue(self, issue_cache_key, error_title, error_mesage, project, **kwargs):
        raise NotImplementedError("Method _create_issue is required")

    @abstractmethod
    def _append_issue(self, issue_cache_key, error_title, error_message, **kwargs):
        raise NotImplementedError("Method _append_issue is required")

    @abstractmethod
    def _fill_issue_cache(self, git_project, issue_cache_key):
        raise NotImplementedError("Method _fill_issue_cache is required")

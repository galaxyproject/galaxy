"""The module describes the ``gitlab`` error plugin plugin."""
from __future__ import absolute_import

import logging

from galaxy.tools.errors import EmailErrorReporter
from galaxy.util import string_as_bool, unicodify
from . import ErrorPlugin

log = logging.getLogger(__name__)


class GitLabPlugin(ErrorPlugin):
    """Send error report to GitLab.
    """
    plugin_type = "gitlab"

    def __init__(self, **kwargs):
        self.app = kwargs['app']
        self.redact_user_details_in_bugreport = self.app.config.redact_user_details_in_bugreport
        self.verbose = string_as_bool(kwargs.get('verbose', False))
        self.user_submission = string_as_bool(kwargs.get('user_submission', False))

        # GitLab settings
        self.gitlab_base_url = kwargs.get('gitlab_base_url', 'https://gitlab.com')
        self.gitlab_default_repo_owner = kwargs.get('gitlab_default_repo_owner', False)
        self.gitlab_default_repo_name = kwargs.get('gitlab_default_repo_name', False)

        try:
            import gitlab
            import requests
            import os

            session = requests.Session()
            session.proxies = {
                'https': os.environ.get('https_proxy'),
                'http': os.environ.get('http_proxy'),
            }
            self.gitlab = gitlab.Gitlab(
                # Allow running against GL enterprise deployments
                kwargs.get('gitlab_base_url', 'https://gitlab.com'),
                private_token=kwargs['gitlab_private_token'],
                session=session
            )
            self.gitlab.auth()

        except ImportError:
            log.error("Please install python-gitlab to submit bug reports to gitlab")
            self.gitlab = None

    def submit_report(self, dataset, job, tool, **kwargs):
        """Submit the error report to GitLab
        """
        log.info(self.gitlab)

        if self.gitlab:
            # Import the necessary libraries
            import sys
            import requests
            if sys.version_info[0] < 3:
                import urllib as urllib
                import urlparse as urlparse
            else:
                import urllib.parse as urllib
                urlparse = urllib

            log.info(job.tool_id)
            log.info(job.tool_version)
            log.info(tool.tool_shed)

            # Determine the ToolShed
            ts_url_request = requests.get('http://' + str(tool.tool_shed))
            ts_url = ts_url_request.url
            log.info("Determined ToolShed is " + ts_url)

            # Find the repo inside the ToolShed
            ts_repo_request = requests.get(ts_url + "/api/repositories?tool_ids=" + str(job.tool_id))
            ts_repo_request_data = ts_repo_request.json()
            ts_repourl = None

            for changeset, repoinfo in ts_repo_request_data.items():
                if isinstance(repoinfo, dict):
                    if 'repository' in repoinfo.keys():
                        if 'remote_repository_url' in repoinfo['repository'].keys():
                            ts_repourl = repoinfo['repository']['remote_repository_url']

            log.info("Determine ToolShed Repository URL: " + ts_repourl)

            if ts_repourl:
                gitlab_projecturl = urlparse.urlparse(ts_repourl).path[1:]
            else:
                gitlab_projecturl = "/".join([self.gitlab_default_repo_owner,
                                              self.gitlab_default_repo_name])

            gitlab_urlencodedpath = urllib.quote_plus(gitlab_projecturl)

            # Make sure we are always logged in, then retrieve the GitLab project
            self.gitlab.auth()
            gl_project = self.gitlab.projects.get(gitlab_urlencodedpath)

            # Get a list of all the issues, parse them for de-duplication later
            log.info(gl_project.issues.list())

            issue_cache = {}
            for issue in gl_project.issues.list():
                if issue.state != 'closed':
                    issue_cache[issue.title] = issue.iid

            # Generate information for the tool
            tool_kw = {'tool_id': unicodify(job.tool_id), 'tool_version': unicodify(job.tool_version)}
            error_title = u"""Galaxy Job Error: {tool_id} v{tool_version}""".format(**tool_kw)

            # We'll re-use the email error reporter's template since GitLab supports HTML
            error_reporter = EmailErrorReporter(dataset.id, self.app)
            error_reporter.create_report(job.get_user(), email=kwargs.get('email', None), message=kwargs.get('message', None), redact_user_details_in_bugreport=self.redact_user_details_in_bugreport)

            # The HTML report
            error_message = error_reporter.html_report

            log.info(error_title in issue_cache)
            if error_title not in issue_cache:
                # Create a new issue.
                issue = gl_project.issues.create({
                    'title': error_title,
                    'description': error_message
                })
                issue_cache[error_title] = issue.iid
            else:
                # Add a comment to an issue...
                gl_url = "/".join([
                    self.gitlab_base_url,
                    "api",
                    "v4",
                    "projects",
                    gitlab_urlencodedpath,
                    "issues",
                    str(issue_cache[error_title]),
                    "notes"
                ])
                self.gitlab.http_post(gl_url, post_data={'body': error_message})
            return ('Submitted error report to GitLab. Your issue number is <a href="%s/%s/issues/%s" target="_blank">#%s</a>.' % (self.gitlab_base_url, gitlab_projecturl, issue_cache[error_title], issue_cache[error_title]), 'success')


__all__ = ('GitLabPlugin', )

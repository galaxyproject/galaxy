"""The module describes the ``github`` error plugin plugin."""
from __future__ import absolute_import

import logging

from galaxy.tools.errors import EmailErrorReporter
from galaxy.util import string_as_bool, unicodify
from . import ErrorPlugin

log = logging.getLogger(__name__)


class GithubPlugin(ErrorPlugin):
    """Send error report to Github.
    """
    plugin_type = "github"

    def __init__(self, **kwargs):
        self.app = kwargs['app']
        self.redact_user_details_in_bugreport = self.app.config.redact_user_details_in_bugreport
        self.verbose = string_as_bool(kwargs.get('verbose', False))
        self.user_submission = string_as_bool(kwargs.get('user_submission', False))
        try:
            import github

            self.github = github.Github(
                kwargs['github_oauth_token'],
                # Allow running against GH enterprise deployments.
                base_url=kwargs.get('github_base_url', 'https://api.github.com')
            )
            self.repo = self.github.get_repo('{github_repo_owner}/{github_repo_name}'.format(**kwargs))
            log.info(self.repo)
            # We want to ensure that we don't generate a thousand issues when
            # multiple users report a bug. So, we need to de-dupe issues. In
            # order to de-dupe, we need to know which are open. So, we'll keep
            # a cache of open issues and just add to it whenever we create a
            # new one.
            self.issue_cache = {}
            for issue in self.repo.get_issues(state='open'):
                log.info(issue)
                self.issue_cache[issue.title] = issue
            log.info(self.issue_cache)

            # We'll also cache labels which we'll use for tagging issues.
            self.label_cache = {}
            for label in self.repo.get_labels():
                log.info(label)
                self.label_cache[label.name] = label
            log.info(self.label_cache)
        except ImportError:
            log.error("Please install pygithub to submit bug reports to github")
            self.github = None

    def get_label(self, label):
        # If we don't have this label, then create it + cache it.
        if label not in self.label_cache:
            self.label_cache[label] = self.repo.create_label(name=label, color='ffffff')

        return self.label_cache[label]

    def submit_report(self, dataset, job, tool, **kwargs):
        """Submit the error report to sentry
        """
        log.info(self.github)

        if self.github:
            tool_kw = {'tool_id': unicodify(job.tool_id), 'tool_version': unicodify(job.tool_version)}
            label = self.get_label('{tool_id}/{tool_version}'.format(**tool_kw))
            error_title = u"""Galaxy Job Error: {tool_id} v{tool_version}""".format(**tool_kw)

            # We'll re-use the email error reporter's template since github supports HTML
            error_reporter = EmailErrorReporter(dataset.id, self.app)
            error_reporter.create_report(job.get_user(), email=kwargs.get('email', None), message=kwargs.get('message', None), redact_user_details_in_bugreport=self.redact_user_details_in_bugreport)

            # The HTML report
            error_message = error_reporter.html_report

            log.info(error_title in self.issue_cache)
            if error_title not in self.issue_cache:
                # Create a new issue.
                self.issue_cache[error_title] = self.repo.create_issue(
                    title=error_title,
                    body=error_message,
                    # Label it with a tag: tool_id/tool_version
                    labels=[label]
                )
            else:
                self.issue_cache[error_title].create_comment(error_message)
            return ('Submitted bug report to Github. Your issue number is %s' % self.issue_cache[error_title].number, 'success')


__all__ = ('GithubPlugin', )

"""The module describes the ``github`` error plugin plugin."""

import logging
from urllib.parse import urlparse

from galaxy.util import (
    string_as_bool,
    unicodify,
)
from .base_git import BaseGitPlugin

log = logging.getLogger(__name__)


class GithubPlugin(BaseGitPlugin):
    """Send error report to GitHub."""

    plugin_type = "github"

    def __init__(self, **kwargs):
        self.app = kwargs["app"]
        self.redact_user_details_in_bugreport = self.app.config.redact_user_details_in_bugreport
        self.verbose = string_as_bool(kwargs.get("verbose", False))
        self.user_submission = string_as_bool(kwargs.get("user_submission", False))

        # GitHub settings
        self.github_base_url = kwargs.get("github_base_url", "https://github.com")
        self.github_api_url = kwargs.get("github_api_url", "https://api.github.com")
        self.git_default_repo_owner = kwargs.get("github_default_repo_owner", False)
        self.git_default_repo_name = kwargs.get("github_default_repo_name", False)
        self.git_default_repo_only = string_as_bool(kwargs.get("github_default_repo_only", True))

        try:
            import github

            self.github = github.Github(
                kwargs["github_oauth_token"],
                # Allow running against GH enterprise deployments.
                base_url=self.github_api_url,
            )
            # Connect to the default repository and fill up the issue cache for it
            repo = self.github.get_repo(f"{self.git_default_repo_owner}/{self.git_default_repo_name}")
            self._fill_issue_cache(repo, "default")

            # We'll also cache labels which we'll use for tagging issues.
            self.label_cache["default"] = {}
            self._fill_label_cache(repo, "default")
        except ImportError:
            log.error("Please install pygithub to submit bug reports to GitHub")
            self.github = None

    def submit_report(self, dataset, job, tool, **kwargs):
        """Submit the error report to sentry"""
        log.info(self.github)

        if self.github:
            # Determine the ToolShed url, initially we connect with HTTP and if redirect to HTTPS is set up,
            # this will be detected by requests and used further down the line. Also cache this so everything is
            # as fast as possible
            log.info(tool.tool_shed)
            ts_url = self._determine_ts_url(tool)
            log.info("GitLab error reporting - Determined ToolShed is %s", ts_url)

            # Find the repo inside the ToolShed
            ts_repourl = self._get_gitrepo_from_ts(job, ts_url)

            # Determine the GitLab project URL and the issue cache key
            github_projecturl = (
                urlparse(ts_repourl).path[1:]
                if (ts_repourl and not self.git_default_repo_only)
                else "/".join((self.git_default_repo_owner, self.git_default_repo_name))
            )
            issue_cache_key = self._get_issue_cache_key(job, ts_repourl)

            # Connect to the repo
            if github_projecturl not in self.git_project_cache:
                self.git_project_cache[github_projecturl] = self.github.get_repo(f"{github_projecturl}")
            gh_project = self.git_project_cache[github_projecturl]

            # Make sure we keep a cache of the issues, per tool in this case
            if issue_cache_key not in self.issue_cache:
                self._fill_issue_cache(gh_project, issue_cache_key)

            # Retrieve label
            label = self.get_label(
                f"{unicodify(job.tool_id)}/{unicodify(job.tool_version)}", gh_project, issue_cache_key
            )

            # Generate information for the tool
            error_title = self._generate_error_title(job)

            # Generate the error message
            error_message = self._generate_error_message(dataset, job, kwargs)

            log.info(error_title in self.issue_cache[issue_cache_key])
            if error_title not in self.issue_cache[issue_cache_key]:
                # Create a new issue.
                self._create_issue(issue_cache_key, error_title, error_message, gh_project, label=label)
            else:
                self._append_issue(issue_cache_key, error_title, error_message)
            return (
                f"Submitted error report to GitHub. Your issue number is [#{self.issue_cache[issue_cache_key][error_title].number}]({self.github_base_url}/{github_projecturl}/issues/{self.issue_cache[issue_cache_key][error_title].number})",
                "success",
            )

    def _create_issue(self, issue_cache_key, error_title, error_mesage, project, **kwargs):
        # Create a new issue.
        self.issue_cache[issue_cache_key][error_title] = project.create_issue(
            title=error_title,
            body=error_mesage,
            # Label it with a tag: tool_id/tool_version
            labels=[kwargs.get("label")],
        )

    def _append_issue(self, issue_cache_key, error_title, error_message, **kwargs):
        # Create comment on an issue
        self.issue_cache[issue_cache_key][error_title].create_comment(error_message)

    def _fill_issue_cache(self, git_project, issue_cache_key):
        # We want to ensure that we don't generate a thousand issues when
        # multiple users report a bug. So, we need to de-dupe issues. In
        # order to de-dupe, we need to know which are open. So, we'll keep
        # a cache of open issues and just add to it whenever we create a
        # new one.
        self.issue_cache[issue_cache_key] = {}
        for issue in git_project.get_issues(state="open"):
            log.info(issue)
            self.issue_cache[issue_cache_key][issue.title] = issue
        log.info(self.issue_cache)

    def _fill_label_cache(self, git_project, issue_cache_key):
        for label in git_project.get_labels():
            log.info(label)
            self.label_cache[issue_cache_key][label.name] = label
        log.info(self.label_cache)

    def get_label(self, label, git_project, issue_cache_key):
        # If we don't have this label, then create it + cache it.
        if issue_cache_key not in self.label_cache:
            self.label_cache[issue_cache_key] = {}
            self._fill_label_cache(git_project, issue_cache_key)

        if label not in self.label_cache[issue_cache_key]:
            self.label_cache[issue_cache_key][label] = git_project.create_label(name=label, color="ffffff")

        return self.label_cache[issue_cache_key][label]


__all__ = ("GithubPlugin",)

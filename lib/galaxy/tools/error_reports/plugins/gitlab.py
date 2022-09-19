"""The module describes the ``gitlab`` error plugin plugin."""

import logging
import os
import urllib.parse

import requests

try:
    import gitlab
except ImportError:
    gitlab = None
from galaxy.util import string_as_bool
from .base_git import BaseGitPlugin

log = logging.getLogger(__name__)


class GitLabPlugin(BaseGitPlugin):
    """Send error report to GitLab."""

    plugin_type = "gitlab"

    def __init__(self, **kwargs):
        self.app = kwargs["app"]
        self.redact_user_details_in_bugreport = self.app.config.redact_user_details_in_bugreport
        self.verbose = string_as_bool(kwargs.get("verbose", False))
        self.user_submission = string_as_bool(kwargs.get("user_submission", False))

        # GitLab settings
        self.gitlab_base_url = kwargs.get("gitlab_base_url", "https://gitlab.com")
        self.gitlab_private_token = kwargs.get("gitlab_private_token", "")
        self.git_default_repo_owner = kwargs.get("gitlab_default_repo_owner", False)
        self.git_default_repo_name = kwargs.get("gitlab_default_repo_name", False)
        self.git_default_repo_only = string_as_bool(kwargs.get("gitlab_default_repo_only", True))
        self.gitlab_use_proxy = string_as_bool(kwargs.get("gitlab_allow_proxy", True))
        self.gitlab_new_issue_on_closed = string_as_bool(kwargs.get("gitlab_new_issue_on_closed", False))
        self.gitlab_labels = kwargs.get("gitlab_labels", [])

        try:
            if gitlab is None:
                raise Exception(
                    "GitLab error reporting plugin is configured, but gitlab is not installed. "
                    "Please install python-gitlab v2.10.0 or higher."
                )
            self.gitlab = self.gitlab_connect()
            self.gitlab.auth()

        except gitlab.GitlabAuthenticationError:
            log.error("GitLab error reporting - Could not authenticate with GitLab.", exc_info=True)
            self.gitlab = None
        except gitlab.GitlabParsingError:
            log.error("GitLab error reporting - Could not parse GitLab message.", exc_info=True)
            self.gitlab = None
        except (gitlab.GitlabConnectionError, gitlab.GitlabHttpError):
            log.error("GitLab error reporting - Could not connect to GitLab.", exc_info=True)
            self.gitlab = None
        except gitlab.GitlabError:
            log.error("GitLab error reporting - General error communicating with GitLab.", exc_info=True)
            self.gitlab = None

    def gitlab_connect(self):
        import gitlab

        session = requests.Session()
        if self.gitlab_use_proxy:
            session.proxies = {
                "https": os.environ.get("https_proxy"),
                "http": os.environ.get("http_proxy"),
            }

        return gitlab.Gitlab(
            # Allow running against GL enterprise deployments
            self.gitlab_base_url,
            private_token=self.gitlab_private_token,
            session=session,
        )

    def submit_report(self, dataset, job, tool, **kwargs):
        """Submit the error report to GitLab"""
        log.info(self.gitlab)

        # Try to connect beforehand, as we might lose connection
        if not self.gitlab:
            self.gitlab = self.gitlab_connect()
            self.gitlab.auth()

        # Ensure we are connected to Gitlab
        if self.gitlab:
            # Import GitLab here for the error handling
            import gitlab

            try:
                log.info(
                    f"GitLab error reporting - submit report - job tool id: {job.tool_id} - job tool version: {job.tool_version} - tool tool_shed: {tool.tool_shed}"
                )

                # Determine the ToolShed url, initially we connect with HTTP and if redirect to HTTPS is set up,
                # this will be detected by requests and used further down the line. Also cache this so everything is
                # as fast as possible
                ts_url = self._determine_ts_url(tool)
                log.info(f"GitLab error reporting - Determined ToolShed is {ts_url}")

                # Find the repo inside the ToolShed
                ts_repourl = self._get_gitrepo_from_ts(job, ts_url)

                # Remove .git from the repository URL if this was specified
                if ts_repourl is not None and ts_repourl.endswith(".git"):
                    ts_repourl = ts_repourl[:-4]

                log.info(f"GitLab error reporting - Determine ToolShed Repository URL: {ts_repourl}")

                # Determine the GitLab project URL and the issue cache key
                gitlab_projecturl = (
                    urllib.parse.urlparse(ts_repourl).path[1:]
                    if (ts_repourl and not self.git_default_repo_only)
                    else "/".join((self.git_default_repo_owner, self.git_default_repo_name))
                )
                issue_cache_key = self._get_issue_cache_key(job, ts_repourl)

                # Make sure we are always logged in, then retrieve the GitLab project if it isn't cached.
                self.gitlab.auth()
                try:
                    if gitlab_projecturl not in self.git_project_cache:
                        self.git_project_cache[gitlab_projecturl] = self.gitlab.projects.get(gitlab_projecturl)
                except gitlab.GitlabGetError:
                    # Handle scenario where the repository doesn't exist so we can still continue
                    log.warning(
                        f"GitLab error reporting - Repository '{gitlab_projecturl}' doesn't exist, using default repository."
                    )
                    # Redo some of the previous steps to recover from such an issue but continue issue creation
                    gitlab_projecturl = "/".join((self.git_default_repo_owner, self.git_default_repo_name))
                    if gitlab_projecturl not in self.git_project_cache:
                        self.git_project_cache[gitlab_projecturl] = self.gitlab.projects.get(gitlab_projecturl)
                gl_project = self.git_project_cache[gitlab_projecturl]

                # Make sure we keep a cache of the issues, per tool in this case
                if issue_cache_key not in self.issue_cache:
                    self._fill_issue_cache(gl_project, issue_cache_key)

                # Generate information for the tool
                error_title = self._generate_error_title(job)

                # Generate the error message
                error_message = self._generate_error_message(dataset, job, kwargs)

                # Determine the user to assign to the issue
                gl_userid = None
                if len(gl_project.commits.list()) > 0:
                    gl_useremail = gl_project.commits.list()[0].attributes["author_email"]
                    if not self.redact_user_details_in_bugreport:
                        log.debug(f"GitLab error reporting - Last author email: {gl_useremail}")
                    if gl_useremail not in self.git_username_id_cache:
                        gl_emailquery = self.gitlab.users.list(search=gl_useremail)
                        log.debug(f"GitLab error reporting - User list: {gl_emailquery}")
                        if len(gl_emailquery) > 0:
                            log.debug("GitLab error reporting - Last Committer user ID: %s" % gl_emailquery[0].get_id())
                            self.git_username_id_cache[gl_useremail] = gl_emailquery[0].get_id()
                    gl_userid = self.git_username_id_cache.get(gl_useremail, None)

                log.info(error_title in self.issue_cache[issue_cache_key])
                if error_title not in self.issue_cache[issue_cache_key]:
                    self._open_issue(
                        error_message, error_title, gitlab_projecturl, gl_project, gl_userid, issue_cache_key
                    )
                else:
                    if not self.gitlab_new_issue_on_closed:
                        # Check if issue is closed, otherwise reopen it
                        issue_id = self.issue_cache[issue_cache_key][error_title]
                        issue = gl_project.issues.get(issue_id)
                        log.info(f"GitLab error reporting - Issue state is {issue.state}")
                        if issue.state == "closed":
                            # Reopen issue
                            issue.state_event = "reopen"
                            issue.save()
                            log.info(f"GitLab error reporting - Reopened issue {issue_id}")

                        # Add a comment to an issue...
                        self._append_issue(
                            issue_cache_key, error_title, error_message, gitlab_projecturl=gitlab_projecturl
                        )
                    else:
                        self._open_issue(
                            error_message, error_title, gitlab_projecturl, gl_project, gl_userid, issue_cache_key
                        )

                return (
                    'Submitted error report to GitLab. Your issue number is <a href="%s/%s/issues/%s" '
                    'target="_blank">#%s</a>.'
                    % (
                        self.gitlab_base_url,
                        gitlab_projecturl,
                        self.issue_cache[issue_cache_key][error_title],
                        self.issue_cache[issue_cache_key][error_title],
                    ),
                    "success",
                )

            except gitlab.GitlabCreateError:
                log.error("GitLab error reporting - Could not create the issue on GitLab.", exc_info=True)
                return ("Internal Error.", "danger")
            except gitlab.GitlabOwnershipError:
                log.error(
                    "GitLab error reporting - Could not create the issue on GitLab due to ownership issues.",
                    exc_info=True,
                )
                return ("Internal Error.", "danger")
            except gitlab.GitlabSearchError:
                log.error("GitLab error reporting - Could not find repository on GitLab.", exc_info=True)
                return ("Internal Error.", "danger")
            except gitlab.GitlabAuthenticationError:
                log.error("GitLab error reporting - Could not authenticate with GitLab.", exc_info=True)
                return ("Internal Error.", "danger")
            except gitlab.GitlabParsingError:
                log.error("GitLab error reporting - Could not parse GitLab message.", exc_info=True)
                return ("Internal Error.", "danger")
            except (gitlab.GitlabConnectionError, gitlab.GitlabHttpError):
                log.error("GitLab error reporting - Could not connect to GitLab.", exc_info=True)
                return ("Internal Error.", "danger")
            except gitlab.GitlabError:
                log.error("GitLab error reporting - General error communicating with GitLab.", exc_info=True)
                return ("Internal Error.", "danger")
            except Exception:
                log.error(
                    "GitLab error reporting - Error reporting to GitLab had an exception that could not be "
                    "determined.",
                    exc_info=True,
                )
                return ("Internal Error.", "danger")
        else:
            log.error("GitLab error reporting - No connection to GitLab. Cannot report error to GitLab.")
            return ("Internal Error.", "danger")

    def _open_issue(self, error_message, error_title, gitlab_projecturl, gl_project, gl_userid, issue_cache_key):
        """Open an issue"""
        try:
            # Create a new issue.
            self._create_issue(issue_cache_key, error_title, error_message, gl_project, gl_userid=gl_userid)
        except (gitlab.GitlabOwnershipError, gitlab.GitlabGetError):
            # Create an issue in the default location
            gitlab_projecturl = "/".join((self.git_default_repo_owner, self.git_default_repo_name))
            # Make sure we are always logged in, then retrieve the GitLab project if it isn't cached.
            self.gitlab = self.gitlab_connect()
            if gitlab_projecturl not in self.git_project_cache:
                self.git_project_cache[gitlab_projecturl] = self.gitlab.projects.get(gitlab_projecturl)
            gl_project = self.git_project_cache[gitlab_projecturl]

            # Submit issue to default project
            self._create_issue(issue_cache_key, error_title, error_message, gl_project, gl_userid=gl_userid)
        return gitlab_projecturl

    def _create_issue(self, issue_cache_key, error_title, error_message, project, **kwargs):
        # Set payload for the issue
        issue_data = {"title": error_title, "description": error_message}

        # Assign the user to the issue
        gl_userid = kwargs.get("gl_userid", None)
        if gl_userid is not None:
            issue_data["assignee_ids"] = [gl_userid]

        # Create the issue on GitLab
        issue = project.issues.create(issue_data)

        # Set labels
        issue.labels = self.gitlab_labels
        issue.save()

        # Store in cache
        self.issue_cache[issue_cache_key][error_title] = issue.iid

    def _append_issue(self, issue_cache_key, error_title, error_message, **kwargs):
        # Add a comment to an existing issue
        gl_url = "/".join(
            (
                self.gitlab_base_url,
                "api",
                "v4",
                "projects",
                kwargs.get("gitlab_projecturl"),
                "issues",
                str(self.issue_cache[issue_cache_key][error_title]),
                "notes",
            )
        )
        self.gitlab.http_post(gl_url, post_data={"body": error_message})

    def _fill_issue_cache(self, git_project, issue_cache_key):
        self.issue_cache[issue_cache_key] = {}
        # Loop over all open issues and add the issue iid to the cache
        for issue in git_project.issues.list():
            if issue.state != "closed":
                log.info("GitLab error reporting - Repo issue: %s", str(issue.iid))
                self.issue_cache[issue_cache_key][issue.title] = issue.iid


__all__ = ("GitLabPlugin",)

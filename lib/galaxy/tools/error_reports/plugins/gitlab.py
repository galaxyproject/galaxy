"""The module describes the ``gitlab`` error plugin plugin."""
from __future__ import absolute_import

import logging
import os
import sys

import requests
if sys.version_info[0] < 3:
    import urllib as urllib
    import urlparse as urlparse
else:
    import urllib.parse as urllib
    urlparse = urllib

from galaxy.util import string_as_bool
from .base_git import BaseGitPlugin

log = logging.getLogger(__name__)


class GitLabPlugin(BaseGitPlugin):
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
        self.git_default_repo_owner = kwargs.get('gitlab_default_repo_owner', False)
        self.git_default_repo_name = kwargs.get('gitlab_default_repo_name', False)
        self.git_default_repo_only = string_as_bool(kwargs.get('gitlab_default_repo_only', True))

        try:
            import gitlab

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
            log.error("GitLab error reporting - Please install python-gitlab to submit bug reports to GitLab.")
            self.gitlab = None
        except gitlab.GitlabAuthenticationError:
            log.error("GitLab error reporting - Could not authenticate with GitLab.")
            self.gitlab = None
        except gitlab.GitlabParsingError:
            log.error("GitLab error reporting - Could not parse GitLab message.")
            self.gitlab = None
        except (gitlab.GitlabConnectionError, gitlab.GitlabHttpError):
            log.error("GitLab error reporting - Could not connect to GitLab.")
            self.gitlab = None
        except gitlab.GitlabError:
            log.error("GitLab error reporting - General error communicating with GitLab.")
            self.gitlab = None

    def submit_report(self, dataset, job, tool, **kwargs):
        """Submit the error report to GitLab
        """
        log.info(self.gitlab)

        if self.gitlab:
            # Import GitLab here for the error handling
            import gitlab
            try:
                log.info("GitLab error reporting - submit report - job tool id: %s - job tool version: %s - tool tool_shed: %s" % (job.tool_id, job.tool_version, tool.tool_shed))

                # Determine the ToolShed url, initially we connect with HTTP and if redirect to HTTPS is set up,
                # this will be detected by requests and used further down the line. Also cache this so everything is
                # as fast as possible
                ts_url = self._determine_ts_url(tool)
                log.info("GitLab error reporting - Determined ToolShed is %s", ts_url)

                # Find the repo inside the ToolShed
                ts_repourl = self._get_gitrepo_from_ts(job, ts_url)

                log.info("GitLab error reporting - Determine ToolShed Repository URL: %s", ts_repourl)

                # Determine the GitLab project URL and the issue cache key
                gitlab_projecturl = urlparse.urlparse(ts_repourl).path[1:] if (ts_repourl and not self.git_default_repo_only)\
                    else "/".join([self.git_default_repo_owner, self.git_default_repo_name])
                issue_cache_key = self._get_issue_cache_key(job, ts_repourl)

                gitlab_urlencodedpath = urllib.quote_plus(gitlab_projecturl)

                # Make sure we are always logged in, then retrieve the GitLab project if it isn't cached.
                self.gitlab.auth()
                if gitlab_projecturl not in self.git_project_cache:
                    self.git_project_cache[gitlab_projecturl] = self.gitlab.projects.get(gitlab_urlencodedpath)
                gl_project = self.git_project_cache[gitlab_projecturl]

                # Make sure we keep a cache of the issues, per tool in this case
                if issue_cache_key not in self.issue_cache:
                    self._fill_issue_cache(gl_project, issue_cache_key)

                # Generate information for the tool
                error_title = self._generate_error_title(job)

                # Generate the error message
                error_message = self._generate_error_message(dataset, job, kwargs)

                log.info(error_title in self.issue_cache[issue_cache_key])
                if error_title not in self.issue_cache[issue_cache_key]:
                    # Create a new issue.
                    self._create_issue(issue_cache_key, error_title, error_message, gl_project)
                else:
                    # Add a comment to an issue...
                    self._append_issue(issue_cache_key, error_title, error_message, gitlab_urlencodedpath=gitlab_urlencodedpath)

                return ('Submitted error report to GitLab. Your issue number is <a href="%s/%s/issues/%s" '
                        'target="_blank">#%s</a>.' % (self.gitlab_base_url, gitlab_projecturl,
                                                      self.issue_cache[issue_cache_key][error_title],
                                                      self.issue_cache[issue_cache_key][error_title]), 'success')

            except gitlab.GitlabCreateError as e:
                log.error("GitLab error reporting - Could not create the issue on GitLab. "
                          "Exception information: " + e.message)
                return ('Internal Error.', 'danger')
            except gitlab.GitlabOwnershipError as e:
                log.error("GitLab error reporting - Could not create the issue on GitLab due to ownership issues. "
                          "Exception information: " + e.message)
                return ('Internal Error.', 'danger')
            except gitlab.GitlabSearchError as e:
                log.error("GitLab error reporting - Could not find repository on GitLab. "
                          "Exception information: " + e.message)
                return ('Internal Error.', 'danger')
            except gitlab.GitlabAuthenticationError as e:
                log.error("GitLab error reporting - Could not authenticate with GitLab. "
                          "Exception information: " + e.message)
                return ('Internal Error.', 'danger')
            except gitlab.GitlabParsingError as e:
                log.error("GitLab error reporting - Could not parse GitLab message. "
                          "Exception information: " + e.message)
                return ('Internal Error.', 'danger')
            except (gitlab.GitlabConnectionError, gitlab.GitlabHttpError) as e:
                log.error("GitLab error reporting - Could not connect to GitLab. Exception information: " + e.message)
                return ('Internal Error.', 'danger')
            except gitlab.GitlabError as e:
                log.error("GitLab error reporting - General error communicating with GitLab. "
                          "Exception information: " + e.message)
                return ('Internal Error.', 'danger')
            except Exception as e:
                log.error("GitLab error reporting - Error reporting to GitLab had an exception that could not be "
                          "determined. Exception information: " + e.message)
                return ('Internal Error.', 'danger')
        else:
            log.error("GitLab error reporting - No connection to GitLab. Cannot report error to GitLab.")
            return ('Internal Error.', 'danger')

    def _create_issue(self, issue_cache_key, error_title, error_mesage, project, **kwargs):
        # Create the issue on GitLab
        issue = project.issues.create({
            'title': error_title,
            'description': error_mesage
        })
        self.issue_cache[issue_cache_key][error_title] = issue.iid

    def _append_issue(self, issue_cache_key, error_title, error_message, **kwargs):
        # Add a comment to an existing issue
        gl_url = "/".join([
            self.gitlab_base_url,
            "api",
            "v4",
            "projects",
            kwargs.get('gitlab_urlencodedpath'),
            "issues",
            str(self.issue_cache[issue_cache_key][error_title]),
            "notes"
        ])
        self.gitlab.http_post(gl_url, post_data={'body': error_message})

    def _fill_issue_cache(self, git_project, issue_cache_key):
        self.issue_cache[issue_cache_key] = {}
        # Loop over all open issues and add the issue iid to the cache
        for issue in git_project.issues.list():
            if issue.state != 'closed':
                log.info("GitLab error reporting - Repo issue: %s", str(issue.iid))
                self.issue_cache[issue_cache_key][issue.title] = issue.iid


__all__ = ('GitLabPlugin', )

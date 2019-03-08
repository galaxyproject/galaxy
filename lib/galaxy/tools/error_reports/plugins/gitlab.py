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

        # Cache for lookups
        self.issue_cache = {}
        self.ts_urls = {}
        self.ts_repo_cache = {}
        self.gitlab_project_cache = {}

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
                log.info("GitLab error reporting - submit report - job tool id: %s - job tool version: %s - "
                         "tool tool_shed: %s", (job.tool_id, job.tool_version, tool.tool_shed))

                # Determine the ToolShed url, initially we connect with HTTP and if redirect to HTTPS is set up,
                # this will be detected by requests and used further down the line. Also cache this so everything is
                # as fast as possible
                if tool.tool_shed not in self.ts_urls:
                    ts_url_request = requests.get('http://' + str(tool.tool_shed))
                    self.ts_urls[tool.tool_shed] = ts_url_request.url
                ts_url = self.ts_urls[tool.tool_shed]
                log.info("GitLab error reporting - Determined ToolShed is " + ts_url)

                # Find the repo inside the ToolShed
                if job.tool_id not in self.ts_repo_cache:
                    ts_repo_request = requests.get(ts_url + "/api/repositories?tool_ids=" + str(job.tool_id))
                    ts_repo_request_data = ts_repo_request.json()

                    for changeset, repoinfo in ts_repo_request_data.items():
                        if isinstance(repoinfo, dict):
                            if 'repository' in repoinfo.keys():
                                if 'remote_repository_url' in repoinfo['repository'].keys():
                                    self.ts_repo_cache[job.tool_id] = repoinfo['repository']['remote_repository_url']

                ts_repourl = self.ts_repo_cache[job.tool_id]

                log.info("GitLab error reporting - Determine ToolShed Repository URL: %s", ts_repourl)

                if ts_repourl:
                    gitlab_projecturl = urlparse.urlparse(ts_repourl).path[1:]
                    issue_cache_key = job.tool_id
                else:
                    gitlab_projecturl = "/".join([self.gitlab_default_repo_owner,
                                                  self.gitlab_default_repo_name])
                    issue_cache_key = "default"

                gitlab_urlencodedpath = urllib.quote_plus(gitlab_projecturl)

                # Make sure we are always logged in, then retrieve the GitLab project if it isn't cached.
                self.gitlab.auth()
                if gitlab_projecturl not in self.gitlab_project_cache:
                    self.gitlab_project_cache[gitlab_projecturl] = self.gitlab.projects.get(gitlab_urlencodedpath)
                gl_project = self.gitlab_project_cache[gitlab_projecturl]

                # Make sure we keep a cache of the issues, per tool in this case
                if issue_cache_key not in self.issue_cache:
                    self.issue_cache[issue_cache_key] = {}

                    # Loop over all open issues and add the issue iid to the cache
                    for issue in gl_project.issues.list():
                        if issue.state != 'closed':
                            log.info("GitLab error reporting - Repo issue: %s", str(issue.iid))
                            self.issue_cache[issue_cache_key][issue.title] = issue.iid

                # Generate information for the tool
                tool_kw = {'tool_id': unicodify(job.tool_id), 'tool_version': unicodify(job.tool_version)}
                error_title = u"""Galaxy Job Error: {tool_id} v{tool_version}""".format(**tool_kw)

                # We'll re-use the email error reporter's template since GitLab supports HTML
                error_reporter = EmailErrorReporter(dataset.id, self.app)
                error_reporter.create_report(job.get_user(), email=kwargs.get('email', None),
                                             message=kwargs.get('message', None),
                                             redact_user_details_in_bugreport=self.redact_user_details_in_bugreport)

                # The HTML report
                error_message = error_reporter.html_report

                log.info(error_title in self.issue_cache[issue_cache_key])
                if error_title not in self.issue_cache[issue_cache_key]:
                    # Create a new issue.
                    issue = gl_project.issues.create({
                        'title': error_title,
                        'description': error_message
                    })
                    self.issue_cache[issue_cache_key][error_title] = issue.iid
                else:
                    # Add a comment to an issue...
                    gl_url = "/".join([
                        self.gitlab_base_url,
                        "api",
                        "v4",
                        "projects",
                        gitlab_urlencodedpath,
                        "issues",
                        str(self.issue_cache[issue_cache_key][error_title]),
                        "notes"
                    ])
                    self.gitlab.http_post(gl_url, post_data={'body': error_message})

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


__all__ = ('GitLabPlugin', )

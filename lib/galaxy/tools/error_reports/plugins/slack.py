"""The module describes the ``slack`` error plugin plugin."""

import logging
import uuid
from typing import (
    Any,
    Dict,
)

from galaxy.util import (
    requests,
    string_as_bool,
)
from .base_git import BaseGitPlugin

log = logging.getLogger(__name__)


class SlackPlugin(BaseGitPlugin):
    """Send error report to Slack."""

    plugin_type = "slack"

    def __init__(self, **kwargs):
        self.app = kwargs["app"]
        self.redact_user_details_in_bugreport = self.app.config.redact_user_details_in_bugreport
        self.verbose = string_as_bool(kwargs.get("verbose", False))
        self.user_submission = string_as_bool(kwargs.get("user_submission", False))
        self.webhook_url = kwargs.get("webhook_url", "https://localhost/")

    def _append_issue(self, *args, **kwargs):
        pass

    def _create_issue(self, *args, **kwargs):
        pass

    def _fill_issue_cache(self, *args, **kwargs):
        pass

    def submit_report(self, dataset, job, tool, **kwargs):
        history_id_encoded = self.app.security.encode_id(dataset.history_id)
        history_view_link = self.app.url_for("/histories/view", id=history_id_encoded, qualified=True)
        error_report_id = str(uuid.uuid4())[0:13]
        title = self._generate_error_title(job)

        blocks: Dict[str, Any] = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"You have a new Galaxy bug report:\n*<{history_view_link}|{title}>*",
                    },
                },
            ]
        }

        if "message" in kwargs and kwargs["message"] is not None:
            message = kwargs["message"].strip().replace("\n", "\n> ")
            blocks["blocks"].extend(
                [{"type": "section", "text": {"type": "mrkdwn", "text": f"*Message*\n> {message}```"}}]
            )

        blocks["blocks"].extend(
            [
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Error Report ID:*\n`{error_report_id}`"},
                        {"type": "mrkdwn", "text": f"*ID:*\n{job.id}"},
                        {"type": "mrkdwn", "text": f"*Destination ID:*\n{job.destination_id}"},
                        {"type": "mrkdwn", "text": f"*Exit Code:*\n{job.exit_code}"},
                        {"type": "mrkdwn", "text": f"*Handler:*\n{job.handler}"},
                        {"type": "mrkdwn", "text": f"*Tool Version:*\n{job.tool_version}"},
                        {"type": "mrkdwn", "text": f"*User:*\n{job.get_user().id}"},
                    ],
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Command Line:*\n```\n{job.command_line[0:2800]}\n```"},
                },
            ]
        )

        if job.stdout:
            blocks["blocks"].extend(
                [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Stdout*\n```\n{job.stdout.strip()[0:2800]}\n```"},
                    }
                ]
            )

        if job.stderr:
            blocks["blocks"].extend(
                [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Stderr*\n```\n{job.stderr.strip()[0:2800]}\n```"},
                    }
                ]
            )

        requests.post(self.webhook_url, json=blocks)
        return (f"Sent report to Slack with ID: {error_report_id}", "success")


__all__ = ("SlackPlugin",)

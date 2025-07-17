"""
Functionality for sending error reports for workflow runs.
"""

import string

import markupsafe

from galaxy import (
    model,
    util,
)
from galaxy.security.validate_user_input import validate_email_str
from galaxy.util import unicodify

error_report_template = """
GALAXY WORKFLOW RUN ERROR REPORT
------------------------

This error report was sent from the Galaxy instance hosted on the server
"${host}"
-----------------------------------------------------------------------------
This is in reference to workflow invocation id ${invocation_id} (${invocation_id_encoded}) from history id ${history_id} (${history_id_encoded})
-----------------------------------------------------------------------------
You should be able to view the history associated with the workflow invocation (${invocation_id_encoded}) for workflow

${workflow_name}

by logging in as a Galaxy admin user to the Galaxy instance referenced above
and pointing your browser to the following link.

${history_view_link}
-----------------------------------------------------------------------------
The user ${email_str} provided the following information:

${message}
-----------------------------------------------------------------------------
(This is an automated message).
"""

error_report_template_html = """
<html>
    <body>
<h1>Galaxy Workflow Run Error Report</h1>
<span class="sub"><i>from</i> <span style="font-family: monospace;"><a href="${host}">${host}</a></span>

<h3>Error Localization</h3>
<table style="margin:1em">
    <tbody>
        <tr><td>Workflow</td><td><a href="${workflow_view_link}">${workflow_name} (${workflow_id}) (${workflow_id_encoded})</a></td></tr>
        <tr style="background-color: #f2f2f2"><td>History</td><td><a href="${history_view_link}">${history_id} (${history_id_encoded})</a></td></tr>
        <tr><td>Workflow Invocation</td><td><a href="${invocation_view_link}">${invocation_id} (${invocation_id_encoded})</a></td></tr>
    </tbody>
</table>

<h3>User Provided Information</h3>

The user <span style="font-family: monospace;">${email_str}</span> provided the following information:

<pre style="white-space: pre-wrap;background: #eeeeee;border:1px solid black;padding:1em;">
${message}
</pre>

<h3>Detailed Invocation Information</h3>

More information about the workflow invocation is available at the <a href="${invocation_view_link}">workflow invocation view</a>.

<table style="margin:1em">
    <tbody>
        <tr><td>Invocation ID</td><td>${invocation_id} (${invocation_id_encoded})</td></tr>
        <tr style="background-color: #f2f2f2"><td>Last Update</td><td>${invocation_update_time}</td></tr>
        <tr><td>Scheduling State</td><td>${invocation_scheduling_state}</td></tr>
        <tr style="background-color: #f2f2f2"><td>Workflow ID</td><td>${workflow_id} (${workflow_id_encoded})</td></tr>
        <tr><td>Workflow Version</td><td>${workflow_version}</td></tr>
        <tr style="background-color: #f2f2f2"><td>Stored Workflow ID</td><td>${stored_workflow_id} (${stored_workflow_id_encoded})</td></tr>
    </tbody>
</table>

This is an automated message. Do not reply to this address.
</body></html>
"""


class WorkflowErrorReporter:
    def __init__(self, invocation, app):
        # Get the invocation
        assert isinstance(invocation, model.WorkflowInvocation), ValueError(
            f"Bad value provided for WorkflowInvocation ({invocation})."
        )
        self.invocation = invocation
        self.workflow = invocation.workflow
        self.history = invocation.history
        self.app = app
        self.report = None

    def _can_access_invocation(self, trans, user):
        if not user:
            return False
        if not trans:
            return False
        if not self.app.workflow_manager.check_security(trans, self.invocation, check_ownership=False):
            return False
        return True

    def create_report(self, user, email="", message="", redact_user_details_in_bugreport=False, **kwd):
        host = self.app.url_for("/", qualified=True)

        invocation_id_encoded = self.app.security.encode_id(self.invocation.id)
        invocation_view_link = self.app.url_for(f"/workflows/invocations/{invocation_id_encoded}", qualified=True)
        invocation_update_time = self.invocation.update_time.strftime("%d/%m/%Y %H:%M:%S")
        invocation_scheduling_state = self.invocation.state

        history_id_encoded = self.app.security.encode_id(self.history.id)
        history_view_link = self.app.url_for("/histories/view", id=history_id_encoded, qualified=True)

        stored_workflow_id_encoded = self.app.security.encode_id(self.workflow.stored_workflow.id)
        workflow_id_encoded = self.app.security.encode_id(self.workflow.id)
        workflow_version = self.workflow.version
        workflow_view_link = self.app.url_for(
            f"/published/workflow?id={stored_workflow_id_encoded}&version={workflow_version}", qualified=True
        )

        # TODO: We could maybe also include the invocation messages, but I believe they often link steps
        # which aren't neccessarily the ones where the first jobs fail.
        # invocation_messages = self.invocation.messages
        # # Format messages for display
        # if invocation_messages:
        #     messages_str = "\n".join([f"- {msg[0].reason}" for msg in invocation_messages])
        # else:
        #     messages_str = "No messages"

        # Build the email message
        if redact_user_details_in_bugreport:
            email_str = "redacted"
            if user:
                email_str += f" (user: {user.id})"
        else:
            if user:
                email_str = f"'{user.email}'"
                if email and user.email != email:
                    email_str += f" (providing preferred contact email '{email}')"
            else:
                email_str = "'%s'" % (email or "anonymous")

        report_variables = dict(
            host=host,
            invocation_id=self.invocation.id,
            invocation_id_encoded=invocation_id_encoded,
            invocation_view_link=invocation_view_link,
            invocation_update_time=invocation_update_time,
            invocation_scheduling_state=invocation_scheduling_state,
            history_id_encoded=history_id_encoded,
            history_id=self.history.id,
            history_view_link=history_view_link,
            stored_workflow_id=self.workflow.stored_workflow.id,
            stored_workflow_id_encoded=stored_workflow_id_encoded,
            workflow_id=self.workflow.id,
            workflow_id_encoded=workflow_id_encoded,
            workflow_version=workflow_version,
            workflow_view_link=workflow_view_link,
            workflow_name=self.workflow.name,
            email_str=email_str,
            message=util.unicodify(message),
        )

        self.report = string.Template(error_report_template).safe_substitute(report_variables)

        # Escape all of the content  for use in the HTML report
        for parameter in report_variables.keys():
            if report_variables[parameter] is not None:
                report_variables[parameter] = markupsafe.escape(unicodify(report_variables[parameter]))

        self.html_report = string.Template(error_report_template_html).safe_substitute(report_variables)

    def _send_report(self, user, email=None, message=None, **kwd):
        return self.report

    def send_report(self, user, email=None, message=None, **kwd):
        if self.report is None:
            self.create_report(user, email=email, message=message, **kwd)
        return self._send_report(user, email=email, message=message, **kwd)


class WorkflowEmailErrorReporter(WorkflowErrorReporter):
    def _send_report(self, user, email=None, message=None, trans=None, **kwd):
        smtp_server = self.app.config.smtp_server
        assert smtp_server, ValueError("Mail is not configured for this Galaxy instance")
        to = self.app.config.error_email_to
        assert to, ValueError("Error reporting has been disabled for this Galaxy instance")

        error_msg = validate_email_str(email)
        if not error_msg and self._can_access_invocation(trans, user):
            to += f", {email.strip()}"
        subject = f"Galaxy workflow run error report from {email}"

        reply_to = user.email if user else None
        return util.send_mail(
            self.app.config.email_from,
            to,
            subject,
            self.report,
            self.app.config,
            html=self.html_report,
            reply_to=reply_to,
        )

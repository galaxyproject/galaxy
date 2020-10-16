"""
Functionality for dealing with tool errors.
"""
import cgi
import string

from galaxy import (
    model,
    util,
    web
)
from galaxy.util import unicodify

error_report_template = """
GALAXY TOOL ERROR REPORT
------------------------

This error report was sent from the Galaxy instance hosted on the server
"${host}"
-----------------------------------------------------------------------------
This is in reference to dataset id ${dataset_id} (${dataset_id_encoded}) from history id ${history_id} (${history_id_encoded})
-----------------------------------------------------------------------------
You should be able to view the history containing the related history item (${hda_id_encoded})

${hid}: ${history_item_name}

by logging in as a Galaxy admin user to the Galaxy instance referenced above
and pointing your browser to the following link.

${history_view_link}
-----------------------------------------------------------------------------
The user ${email_str} provided the following information:

${message}
-----------------------------------------------------------------------------
info url: ${hda_show_params_link}
job id: ${job_id} (${job_id_encoded})
tool id: ${job_tool_id}
tool version: ${tool_version}
job pid or drm id: ${job_runner_external_id}
job tool version: ${job_tool_version}
-----------------------------------------------------------------------------
job command line:
${job_command_line}
-----------------------------------------------------------------------------
job stderr:
${job_stderr}
-----------------------------------------------------------------------------
job stdout:
${job_stdout}
-----------------------------------------------------------------------------
job info:
${job_info}
-----------------------------------------------------------------------------
job traceback:
${job_traceback}
-----------------------------------------------------------------------------
(This is an automated message).
"""

error_report_template_html = """
<html>
    <body>
<h1>Galaxy Tool Error Report</h1>
<span class="sub"><i>from</i> <span style="font-family: monospace;"><a href="${host}">${host}</a></span>

<h3>Error Localization</h3>
<table style="margin:1em">
    <tbody>
        <tr><td>Dataset</td><td><a href="${hda_show_params_link}">${dataset_id} (${dataset_id_encoded})</a></td></tr>
        <tr style="background-color: #f2f2f2"><td>History</td><td><a href="${history_view_link}">${history_id} (${history_id_encoded})</a></td></tr>
        <tr><td>Failed Job</td><td>${hid}: ${history_item_name} (${hda_id_encoded})</td></tr>
    </tbody>
</table>

<h3>User Provided Information</h3>

The user <span style="font-family: monospace;">${email_str}</span> provided the following information:

<pre style="white-space: pre-wrap;background: #eeeeee;border:1px solid black;padding:1em;">
${message}
</pre>


<h3>Detailed Job Information</h3>

Job environment and execution information is available at the job <a href="${hda_show_params_link}">info page</a>.

<table style="margin:1em">
    <tbody>
        <tr><td>Job ID</td><td>${job_id} (${job_id_encoded})</td></tr>
        <tr style="background-color: #f2f2f2"><td>Tool ID</td><td>${job_tool_id}</td></tr>
        <tr><td>Tool Version</td><td>${tool_version}</td></tr>
        <tr style="background-color: #f2f2f2"><td>Job PID or DRM id</td><td>${job_runner_external_id}</td></tr>
        <tr><td>Job Tool Version</td><td>${job_tool_version}</td></tr>
    </tbody>
</table>

<h3>Job Execution and Failure Information</h3>

<h4>Command Line</h4>
<pre style="white-space: pre-wrap;background: #eeeeee;border:1px solid black;padding:1em;">
${job_command_line}
</pre>

<h4>stderr</h4>
<pre style="white-space: pre-wrap;background: #eeeeee;border:1px solid black;padding:1em;">
${job_stderr}
</pre>

<h4>stdout</h4>
<pre style="white-space: pre-wrap;background: #eeeeee;border:1px solid black;padding:1em;">
${job_stdout}
</pre>

<h4>Job Information</h4>
<pre style="white-space: pre-wrap;background: #eeeeee;border:1px solid black;padding:1em;">
${job_info}
</pre>

<h4>Job Traceback</h4>
<pre style="white-space: pre-wrap;background: #eeeeee;border:1px solid black;padding:1em;">
${job_traceback}
</pre>

This is an automated message. Do not reply to this address.
</body></html>
"""


class ErrorReporter(object):
    def __init__(self, hda, app):
        # Get the dataset
        sa_session = app.model.context
        if not isinstance(hda, model.HistoryDatasetAssociation):
            hda_id = hda
            try:
                hda = sa_session.query(model.HistoryDatasetAssociation).get(hda_id)
                assert hda is not None, ValueError("No HDA yet")
            except Exception:
                hda = sa_session.query(model.HistoryDatasetAssociation).get(app.security.decode_id(hda_id))
        assert isinstance(hda, model.HistoryDatasetAssociation), ValueError("Bad value provided for HDA (%s)." % (hda))
        self.hda = hda
        # Get the associated job
        self.job = hda.creating_job
        self.app = app
        self.tool_id = self.job.tool_id
        self.report = None

    def _can_access_dataset(self, user):
        if user:
            roles = user.all_roles()
        else:
            roles = []
        return self.app.security_agent.can_access_dataset(roles, self.hda.dataset)

    def create_report(self, user, email='', message='', redact_user_details_in_bugreport=False, **kwd):
        hda = self.hda
        job = self.job
        host = web.url_for('/', qualified=True)
        history_id_encoded = self.app.security.encode_id(hda.history_id)
        history_view_link = web.url_for("/histories/view", id=history_id_encoded, qualified=True)
        hda_id_encoded = self.app.security.encode_id(hda.id)
        hda_show_params_link = web.url_for(controller="dataset", action="show_params", dataset_id=hda_id_encoded, qualified=True)
        # Build the email message
        if redact_user_details_in_bugreport:
            # This is sub-optimal but it is hard to solve fully. This affects
            # the GitHub posting method more than the traditional email plugin.
            # There is no way around CCing the person with the traditional
            # email bug report plugin, however with the GitHub plugin we can
            # submit to GitHub without putting the email in the bug report.
            #
            # A secondary system with access to the GitHub issue and access to
            # the Galaxy database can shuttle email back and forth between
            # GitHub comments and user-emails.
            # Thus preventing issue helpers from every knowing the identity of
            # the bug reporter (and preventing information about the bug
            # reporter from leaving the EU until it hits email directly to the
            # user.)
            email_str = 'redacted'
            if user:
                email_str += ' (user: %s)' % user.id
        else:
            if user:
                email_str = "'%s'" % user.email
                if email and user.email != email:
                    email_str += " (providing preferred contact email '%s')" % email
            else:
                email_str = "'%s'" % (email or 'anonymous')

        report_variables = dict(
            host=host,
            dataset_id_encoded=self.app.security.encode_id(hda.dataset_id),
            dataset_id=hda.dataset_id,
            history_id_encoded=history_id_encoded,
            history_id=hda.history_id,
            hda_id_encoded=hda_id_encoded,
            hid=hda.hid,
            history_item_name=hda.get_display_name(),
            history_view_link=history_view_link,
            hda_show_params_link=hda_show_params_link,
            job_id_encoded=self.app.security.encode_id(job.id),
            job_id=job.id,
            tool_version=job.tool_version,
            job_tool_id=job.tool_id,
            job_tool_version=hda.tool_version,
            job_runner_external_id=job.job_runner_external_id,
            job_command_line=job.command_line,
            job_stderr=util.unicodify(job.stderr),
            job_stdout=util.unicodify(job.stdout),
            job_info=util.unicodify(job.info),
            job_traceback=util.unicodify(job.traceback),
            email_str=email_str,
            message=util.unicodify(message)
        )

        self.report = string.Template(error_report_template).safe_substitute(report_variables)

        # Escape all of the content  for use in the HTML report
        for parameter in report_variables.keys():
            if report_variables[parameter] is not None:
                report_variables[parameter] = cgi.escape(unicodify(report_variables[parameter]))

        self.html_report = string.Template(error_report_template_html).safe_substitute(report_variables)

    def _send_report(self, user, email=None, message=None, **kwd):
        return self.report

    def send_report(self, user, email=None, message=None, **kwd):
        if self.report is None:
            self.create_report(user, email=email, message=message, **kwd)
        return self._send_report(user, email=email, message=message, **kwd)


class EmailErrorReporter(ErrorReporter):
    def _send_report(self, user, email=None, message=None, **kwd):
        smtp_server = self.app.config.smtp_server
        assert smtp_server, ValueError("Mail is not configured for this Galaxy instance")
        to_address = self.app.config.error_email_to
        assert to_address, ValueError("Error reporting has been disabled for this Galaxy instance")

        frm = to_address
        # Check email a bit
        email = email or ''
        email = email.strip()
        parts = email.split()
        if len(parts) == 1 and len(email) > 0 and self._can_access_dataset(user):
            to = to_address + ", " + email
        else:
            to = to_address
        subject = "Galaxy tool error report from %s" % email
        try:
            subject = "%s (%s)" % (subject, self.app.toolbox.get_tool(self.job.tool_id, self.job.tool_version).old_id)
        except Exception:
            pass

        # Send it
        return util.send_mail(frm, to, subject, self.report, self.app.config, html=self.html_report)

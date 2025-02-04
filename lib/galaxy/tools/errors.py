"""
Functionality for dealing with tool errors.
"""
import markupsafe
import json

from galaxy import (
    model,
    util,
)
from galaxy.security.validate_user_input import validate_email_str
from galaxy.util import unicodify
from galaxy.config import templates

REPORT_TEMPLATE_DATASET_TXT = "mail/error-report-dataset.txt"
REPORT_TEMPLATE_DATASET_HTML = "mail/error-report-dataset.html"
REPORT_TEMPLATE_TOOL_TXT = "mail/error-report-tool.txt"
REPORT_TEMPLATE_TOOL_HTML = "mail/error-report-tool.html"

class ErrorReporter:
    def __init__(self, hda, app):
        # Get the dataset
        sa_session = app.model.context
        if not isinstance(hda, model.HistoryDatasetAssociation):
            hda_id = hda
            try:
                hda = sa_session.get(model.HistoryDatasetAssociation, hda_id)
                assert hda is not None, ValueError("No HDA yet")
            except Exception:
                hda = sa_session.get(model.HistoryDatasetAssociation, app.security.decode_id(hda_id))
        assert isinstance(hda, model.HistoryDatasetAssociation), ValueError(f"Bad value provided for HDA ({hda}).")
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

    def create_report(self, user, email="", message="", redact_user_details_in_bugreport=False, **kwd):
        email_str = ReportPresenter._redact_email(user, email, redact_user_details_in_bugreport)
        hda = self.hda
        job = self.job
        host = self.app.url_for("/", qualified=True)
        history_id_encoded = self.app.security.encode_id(hda.history_id)
        history_view_link = self.app.url_for("/histories/view", id=history_id_encoded, qualified=True)
        hda_id_encoded = self.app.security.encode_id(hda.id)
        hda_show_params_link = self.app.url_for(
            controller="dataset", action="details", dataset_id=hda_id_encoded, qualified=True
        )
        # Build the email message

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
            message=util.unicodify(message),
        )
        self.report = ReportPresenter._get_body(self, REPORT_TEMPLATE_DATASET_TXT, self.app.config.templates_dir, report_variables)
        self.html_report = ReportPresenter._get_body(self, REPORT_TEMPLATE_DATASET_HTML, self.app.config.templates_dir, ReportPresenter._escape_html(report_variables))

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
        to = self.app.config.error_email_to
        assert to, ValueError("Error reporting has been disabled for this Galaxy instance")

        error_msg = validate_email_str(email)
        if not error_msg and self._can_access_dataset(user):
            to += f", {email.strip()}"
        subject = f"Galaxy tool error report from {email}"
        try:
            subject = f"{subject} ({self.app.toolbox.get_tool(self.job.tool_id, self.job.tool_version).old_id})"
        except Exception:
            pass

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

class EmailErrorReporterTool:
    def create_report_tool(
        self, 
        user, 
        reportable_data,
        email="", 
        message="",
        redact_user_details_in_bugreport=False, 
        **kwd
    ):
        try:
            email_str = ReportPresenter._redact_email(user, email, redact_user_details_in_bugreport)
            history_id = self.history.id
            history_id_encoded=self.app.security.encode_id(history_id)
            job_tool_id = reportable_data.get("tool_id", None)
            tool_version = reportable_data.get("tool_version", None)
            report_variables = dict(
                host=self.app.url_for("/", qualified=True),
                history_id=history_id,
                history_id_encoded=history_id_encoded,
                history_view_link=self.app.url_for("/histories/view", id=history_id_encoded, qualified=True),
                job_tool_id=job_tool_id,
                job_tool_version=tool_version,
                transcript=json.dumps(reportable_data, indent=4, ensure_ascii=False),
                email_str=email_str,
                message=util.unicodify(message),
            )
            body = templates.render(REPORT_TEMPLATE_TOOL_TXT, report_variables, self.app.config.templates_dir)
            html = templates.render(REPORT_TEMPLATE_TOOL_HTML, ReportPresenter._escape_html(report_variables), self.app.config.templates_dir)       
            subject = ReportPresenter._get_subject(self, email, job_tool_id, tool_version)
            email_to = ReportPresenter._get_email_to(email, self.app.config.error_email_to)
            ReportEmailer().send_report(user, email=email_to, message=message, subject=subject, body=body, html=html)
            return [["Your error report has been sent", "success"]]
        except Exception as e:
            msg = f"An error occurred sending the report by email: {unicodify(e)}"
            return (msg, "danger")


class ReportPresenter:
    def _get_email_to(email, error_email_to):
        error_msg = validate_email_str(email)
        if not error_msg:
            return f"{error_email_to}, {email.strip()}"
        return error_email_to

    def _get_subject(self, email, tool_id, tool_version):
        subject = f"Galaxy tool error report from {email}"
        try:
            subject = f"{subject} ({self.app.toolbox.get_tool(tool_id, tool_version).old_id})"
        except Exception:
            pass
        return subject

    def _get_body(self, template_file, template_directory, template_variables):
        return templates.render(template_file, template_variables, template_directory)

    def _escape_html(content):
        # Escape all of the dynamic-content for use in the HTML report
        for parameter in content.keys():
            if content[parameter] is not None:
                content[parameter] = markupsafe.escape(unicodify(content[parameter]))
        return content

    def _redact_email(user, email=None, redact_user_details_in_bugreport=False) -> str:
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
        return email_str

class ReportEmailer:
    def send_report(self, user, email=None, message=None, **kwd):
        smtp_server = self.app.config.smtp_server
        assert smtp_server, ValueError("Mail is not configured for this Galaxy instance")
        to = self.app.config.error_email_to
        assert to, ValueError("Error reporting has been disabled for this Galaxy instance")

        error_msg = validate_email_str(email)
        if not error_msg and self._can_access_dataset(user):
            to += f", {email.strip()}"
        subject = f"Galaxy tool error report from {email}"
        try:
            subject = f"{subject} ({self.app.toolbox.get_tool(self.job.tool_id, self.job.tool_version).old_id})"
        except Exception:
            pass

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

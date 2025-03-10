import json
import shutil
import tempfile
from pathlib import Path

from galaxy import model
from galaxy.app_unittest_utils.tools_support import UsesApp
from galaxy.tools.errors import EmailErrorReporter
from galaxy.util.unittest import TestCase

# The email the user created their account with.
TEST_USER_EMAIL = "mockgalaxyuser@galaxyproject.org"
# The email the user supplied when submitting the error
TEST_USER_SUPPLIED_EMAIL = "fake@example.org"
TEST_SERVER_EMAIL_FROM = "email_from@galaxyproject.org"
TEST_SERVER_ERROR_EMAIL_TO = "admin@email.to"  # setup in mock config


class TestErrorReporter(TestCase, UsesApp):

    def setUp(self):
        self.setup_app()
        self.app.config.email_from = TEST_SERVER_EMAIL_FROM
        self.tmp_path = Path(tempfile.mkdtemp())
        self.email_path = self.tmp_path / "email.json"
        smtp_server = f"mock_emails_to_path://{self.email_path}"
        self.app.config.smtp_server = smtp_server  # type: ignore[attr-defined]

    def tearDown(self):
        shutil.rmtree(self.tmp_path)

    def test_basic(self):
        user, hda = self._setup_model_objects()

        email_path = self.email_path
        assert not email_path.exists()
        error_report = EmailErrorReporter(hda, self.app)
        error_report.send_report(user, email=TEST_USER_SUPPLIED_EMAIL, message="My custom message")
        assert email_path.exists()
        text = email_path.read_text()
        email_json = json.loads(text)
        assert email_json["from"] == TEST_SERVER_EMAIL_FROM
        assert email_json["to"] == f"{TEST_SERVER_ERROR_EMAIL_TO}, {TEST_USER_SUPPLIED_EMAIL}"
        assert f"Galaxy tool error report from {TEST_USER_SUPPLIED_EMAIL}" == email_json["subject"]
        assert "cat1" in email_json["body"]
        assert "cat1" in email_json["html"]
        assert TEST_USER_EMAIL == email_json["reply_to"]

    def test_hda_security(self, tmp_path):
        user, hda = self._setup_model_objects()
        error_report = EmailErrorReporter(hda, self.app)
        security_agent = self.app.security_agent
        private_role = security_agent.create_private_user_role(user)
        access_action = security_agent.permitted_actions.DATASET_ACCESS.action
        manage_action = security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action
        permissions = {access_action: [private_role], manage_action: [private_role]}
        security_agent.set_all_dataset_permissions(hda.dataset, permissions)

        other_user = model.User(email="otheruser@galaxyproject.org", password="mockpass2")
        self._commit_objects([other_user])
        security_agent = self.app.security_agent
        email_path = self.email_path
        assert not email_path.exists()
        error_report.send_report(other_user, email=TEST_USER_SUPPLIED_EMAIL, message="My custom message")
        # Without permissions, the email still gets sent but the supplied email is ignored
        # I'm not saying this is the right behavior but it is what the code does at the time of test
        # writing -John
        assert email_path.exists()
        text = email_path.read_text()
        email_json = json.loads(text)
        assert "otheruser@galaxyproject.org" not in email_json["to"]

    def test_html_sanitization(self, tmp_path):
        user, hda = self._setup_model_objects()
        email_path = self.email_path
        assert not email_path.exists()
        error_report = EmailErrorReporter(hda, self.app)
        error_report.send_report(
            user, email=TEST_USER_SUPPLIED_EMAIL, message='My custom <a href="http://sneaky.com/">message</a>'
        )
        assert email_path.exists()
        text = email_path.read_text()
        email_json = json.loads(text)
        html = email_json["html"]
        assert "&lt;a href=&#34;http://sneaky.com/&#34;&gt;message&lt;/a&gt;" in html

    def test_redact_user_details_in_bugreport(self, tmp_path):
        user, hda = self._setup_model_objects()

        email_path = self.email_path
        assert not email_path.exists()
        error_report = EmailErrorReporter(hda, self.app)
        error_report.send_report(
            user, email=TEST_USER_SUPPLIED_EMAIL, message="My custom message", redact_user_details_in_bugreport=True
        )
        assert email_path.exists()
        text = email_path.read_text()
        email_json = json.loads(text)
        assert "The user redacted (user: 1) provided the following information:" in email_json["body"]
        assert (
            """The user <span style="font-family: monospace;">redacted (user: 1)</span> provided the following information:"""
            in email_json["html"]
        )

    def test_no_redact_user_details_in_bugreport(self, tmp_path):
        user, hda = self._setup_model_objects()

        email_path = self.email_path
        assert not email_path.exists()
        error_report = EmailErrorReporter(hda, self.app)
        error_report.send_report(
            user, email=TEST_USER_SUPPLIED_EMAIL, message="My custom message", redact_user_details_in_bugreport=False
        )
        assert email_path.exists()
        text = email_path.read_text()
        email_json = json.loads(text)
        assert (
            f"The user '{TEST_USER_EMAIL}' (providing preferred contact email '{TEST_USER_SUPPLIED_EMAIL}') provided the following information:"
            in email_json["body"]
        )
        assert (
            f"""The user <span style="font-family: monospace;">&#39;{TEST_USER_EMAIL}&#39; (providing preferred contact email &#39;{TEST_USER_SUPPLIED_EMAIL}&#39;)</span> provided the following information:"""
            in email_json["html"]
        )

    def _setup_model_objects(self):
        user = model.User(email=TEST_USER_EMAIL, password="mockpass")
        job = model.Job()
        job.tool_id = "cat1"
        job.history = model.History()
        job.user = user
        job.history.user = user
        hda = model.HistoryDatasetAssociation(history=job.history)
        hda.dataset = model.Dataset()
        hda.dataset.state = "ok"
        job.add_output_dataset("out1", hda)
        self._commit_objects([job, hda, user])
        return user, hda

    def _commit_objects(self, objects):
        session = self.app.model.context
        session.add_all(objects)
        session.commit()

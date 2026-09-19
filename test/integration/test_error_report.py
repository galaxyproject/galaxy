"""Integration tests for user error reporting."""

import json
import os
import string

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

JSON_ERROR_REPORTS = """
- type: json
  verbose: true
  user_submission: true
  directory: ${reports_directory}
"""

MOCK_EMAIL_ERROR_REPORTS = """
- type: email
  verbose: true
  user_submission: true
"""


class TestErrorReportIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    reports_directory: str
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        reports_directory = cls._test_driver.mkdtemp()
        cls.reports_directory = reports_directory
        template = string.Template(JSON_ERROR_REPORTS)
        reports_yaml = template.safe_substitute({"reports_directory": reports_directory})
        reports_conf = os.path.join(reports_directory, "error_report.yml")
        with open(reports_conf, "w") as f:
            f.write(reports_yaml)
        config["error_report_file"] = reports_conf

    def test_basic_tool_error(self):
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_populator.run_detect_errors(history_id, 6, "my stdout", "my stderr")
            job_id = response["jobs"][0]["id"]
            dataset_result = response["outputs"][0]
            self.dataset_populator.report_job_error(job_id, dataset_result["id"])
            assert len(os.listdir(self.reports_directory)) == 2
            error_json = self.read_error_report(job_id)
            error_dict = json.loads(error_json)
            assert error_dict["exit_code"] == 6

    def test_tool_error_custom_message_and_email(self):
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_populator.run_detect_errors(history_id, 6, "my stdout", "my stderr")
            job_id = response["jobs"][0]["id"]
            dataset_result = response["outputs"][0]
            self.dataset_populator.report_job_error(
                job_id, dataset_result["id"], "some new details", "notreal@galaxyproject.org"
            )
            error_json = self.read_error_report(job_id)
            error_dict = json.loads(error_json)
            assert error_dict["exit_code"] == 6
            assert error_dict["message"] == "some new details"
            assert error_dict["email"] == "notreal@galaxyproject.org"

    def read_error_report(self, job_id: str):
        app = self._app
        job_id_decoded = app.security.decode_id(job_id)
        with open(os.path.join(self.reports_directory, str(job_id_decoded))) as f:
            return f.read()


class TestErrorEmailReportIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    reports_directory: str
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        reports_directory = cls._test_driver.mkdtemp()
        cls.reports_directory = reports_directory
        template = string.Template(MOCK_EMAIL_ERROR_REPORTS)
        reports_yaml = template.safe_substitute({"reports_directory": reports_directory})
        reports_conf = os.path.join(reports_directory, "error_report.yml")
        with open(reports_conf, "w") as f:
            f.write(reports_yaml)
        config["error_report_file"] = reports_conf
        config["smtp_server"] = f"mock_emails_to_path://{reports_directory}/email.json"
        config["error_email_to"] = "jsonfiles@thefilesystem.org"

    def test_tool_error_custom_message_and_email(self):
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_populator.run_detect_errors(history_id, 6, "my stdout", "my stderr")
            job_id = response["jobs"][0]["id"]
            dataset_result = response["outputs"][0]
            self.dataset_populator.report_job_error(
                job_id, dataset_result["id"], "some new details", "notreal@galaxyproject.org"
            )
            error_json = self.read_most_recent_error_report()
            error_dict = json.loads(error_json)
            assert error_dict["to"] == "jsonfiles@thefilesystem.org, notreal@galaxyproject.org"
            assert error_dict["subject"] == "Galaxy tool error report from notreal@galaxyproject.org (detect_errors)"
            assert "<h1>Galaxy Tool Error Report</h1>" in error_dict["html"]

    def read_most_recent_error_report(self):
        with open(os.path.join(self.reports_directory, "email.json")) as f:
            return f.read()

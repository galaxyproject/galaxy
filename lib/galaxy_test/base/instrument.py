""" Utilities to help instrument tool tests.

Including structured data nose plugin that allows storing arbitrary structured
data on a per test case basis - used by tool test to store inputs,
output problems, job tests, etc... but could easily by used by other test
types in a different way.
"""

import json
import threading

from nose.plugins import Plugin

NO_JOB_DATA = object()
JOB_DATA = threading.local()
JOB_DATA.new = True
JOB_DATA.data = NO_JOB_DATA


def register_job_data(data):
    if not JOB_DATA.new:
        return
    JOB_DATA.data = data
    JOB_DATA.new = False


def fetch_job_data():
    try:
        if JOB_DATA.new:
            return NO_JOB_DATA
        else:
            return JOB_DATA.data
    finally:
        JOB_DATA.new = True


class StructuredTestDataPlugin(Plugin):
    name = "structureddata"

    def options(self, parser, env):
        super().options(parser, env=env)
        parser.add_option(
            "--structured-data-file",
            action="store",
            dest="structured_data_file",
            metavar="FILE",
            default=env.get("NOSE_STRUCTURED_DATA", "structured_test_data.json"),
            help=(
                "Path to JSON file to store the Galaxy structured data report in."
                "Default is structured_test_data.json in the working directory "
                "[NOSE_STRUCTURED_DATA]"
            ),
        )

    def configure(self, options, conf):
        super().configure(options, conf)
        self.conf = conf
        if not self.enabled:
            return
        self.tests = []
        self.structured_data_report_file = open(options.structured_data_file, "w")

    def finalize(self, result):
        pass

    def _handle_result(self, test, *args, **kwds):
        job_data = fetch_job_data()
        id = test.id()
        has_data = job_data is not NO_JOB_DATA
        entry = {
            "id": id,
            "has_data": has_data,
            "data": job_data if has_data else None,
        }
        self.tests.append(entry)

    addError = _handle_result
    addFailure = _handle_result
    addSuccess = _handle_result

    def report(self, stream):
        report_obj = {
            "version": "0.1",
            "tests": self.tests,
        }
        json.dump(report_obj, self.structured_data_report_file)
        self.structured_data_report_file.close()

import json
import os
import subprocess
import sys

from galaxy.app_unittest_utils import tools_support
from galaxy.util import galaxy_directory
from galaxy.util.unittest import TestCase

EXPRESSION_TOOL = os.path.join(galaxy_directory(), "test", "functional", "tools", "expression_forty_two.xml")


class TestExpressionToolJobFiles(TestCase, tools_support.UsesTools):
    def setUp(self):
        super().setUp()
        self.setup_app()
        self._init_tool_for_path(EXPRESSION_TOOL)

    def tearDown(self):
        self.tear_down_app()

    def test_job_files_are_in_configs_directory(self):
        # Tool containers can mount configs/, outputs/ and working/ of the job directory without the job directory itself.
        job_directory = os.path.join(self.test_directory, "job")
        working_directory = os.path.join(job_directory, "working")
        outputs_directory = os.path.join(job_directory, "outputs")
        os.makedirs(working_directory)
        os.makedirs(outputs_directory)
        output_path = os.path.join(outputs_directory, "out1.json")

        self.tool.exec_before_job(
            self.app,
            {},
            {"out1": None},
            param_dict={"__local_working_directory__": job_directory, "out1": output_path},
        )
        assert sorted(os.listdir(job_directory)) == ["configs", "outputs", "working"]

        environment = {variable["name"]: variable["template"] for variable in self.tool.environment_variables}
        env = dict(
            os.environ,
            GALAXY_EXPRESSION_INPUTS=environment["GALAXY_EXPRESSION_INPUTS"],
            PATH=f"{os.path.dirname(sys.executable)}{os.pathsep}{os.environ['PATH']}",
            PYTHONPATH=os.path.join(galaxy_directory(), "lib"),
        )
        # Galaxy runs tool commands from the tool working directory.
        subprocess.run(["sh", "-c", self.tool.command], cwd=working_directory, env=env, check=True)
        with open(output_path) as f:
            assert json.load(f) == 42

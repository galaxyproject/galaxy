import json
import os
import shutil
import subprocess
import tempfile

from galaxy.tools import expressions
from galaxy.util import galaxy_directory
from galaxy.util.unittest_utils import skip_unless_executable

LIB_DIRECTORY = os.path.join(galaxy_directory(), "lib")


@skip_unless_executable("node")
def test_run_simple():
    test_directory = tempfile.mkdtemp()
    try:
        environment_path = os.path.join(test_directory, "env.json")
        environment = {
            "job": {"input1": "7"},
            "outputs": [{"name": "out1", "from_expression": "output1", "path": "moo"}],
            "script": "{return {'output1': parseInt($job.input1)};}",
        }
        with open(environment_path, "w") as f:
            json.dump(environment, f)
        expressions.write_evalute_script(
            test_directory,
        )
        new_env = os.environ.copy()
        if "PYTHONPATH" in new_env:
            new_env["PYTHONPATH"] = "{}:{}".format(LIB_DIRECTORY, new_env["PYTHONPATH"])
        else:
            new_env["PYTHONPATH"] = LIB_DIRECTORY
        new_env["GALAXY_EXPRESSION_INPUTS"] = environment_path
        subprocess.check_call(
            args=expressions.EXPRESSION_SCRIPT_CALL,
            shell=True,
            cwd=test_directory,
            env=new_env,
        )
        with open(os.path.join(test_directory, "moo")) as f:
            out_content = f.read()
        assert out_content == "7", out_content
    finally:
        shutil.rmtree(test_directory)

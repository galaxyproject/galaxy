import os

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.tool_util_models.tool_source import (
    XmlTemplateConfigFile,
    YamlTemplateConfigFile,
)
from galaxy.tools.evaluation import (
    ToolEvaluator,
    UserToolEvaluator,
)
from galaxy.util.bunch import Bunch


def _evaluator(evaluator_class, job_directory, config_file):
    app = Bunch(config=Bunch(expression_evaluation_isolation_command=""))
    tool = Bunch(config_files=[config_file], javascript_requirements=None, python_template_version="3")
    evaluator = evaluator_class(app, tool, None, str(job_directory))
    evaluator.param_dict = {"inputs": {}, "outdir": str(job_directory / "working")}
    evaluator.compute_environment = Bunch(config_directory=lambda: "/compute/configs", sep=lambda: "/")
    return evaluator


@pytest.fixture
def job_directory(tmp_path):
    job_directory = tmp_path / "job"
    (job_directory / "working").mkdir(parents=True)
    return job_directory


def _escaping_filenames(tmp_path, job_directory):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (job_directory / "working" / "link").symlink_to(elsewhere)
    return ["../x", "sub/../../x", str(elsewhere / "x"), "link/x"]


@pytest.mark.parametrize("filename", ["script.sh", "sub/dir/script.sh"])
def test_user_tool_config_file_linked_into_working_directory(job_directory, filename):
    config_file = YamlTemplateConfigFile(name="script", filename=filename, content="echo hi")
    evaluator = _evaluator(UserToolEvaluator, job_directory, config_file)
    evaluator._build_config_files()
    assert (job_directory / "working" / filename).read_text() == "echo hi"


def test_tool_config_file_linked_into_working_subdirectory(job_directory):
    config_file = XmlTemplateConfigFile(name="script", filename="sub/script.sh", content="echo hi")
    evaluator = _evaluator(ToolEvaluator, job_directory, config_file)
    evaluator._build_config_files()
    assert (job_directory / "working" / "sub" / "script.sh").read_text() == "echo hi"


def test_user_tool_config_file_outside_working_directory_refused(tmp_path, job_directory):
    for filename in _escaping_filenames(tmp_path, job_directory):
        # model_construct skips the filename validator, so only the evaluator check applies.
        config_file = YamlTemplateConfigFile.model_construct(name="script", filename=filename, content="echo hi")
        evaluator = _evaluator(UserToolEvaluator, job_directory, config_file)
        with pytest.raises(RequestParameterInvalidException):
            evaluator._build_config_files()
    assert sorted(os.listdir(job_directory)) == ["configs", "working"]
    assert not (tmp_path / "elsewhere" / "x").exists()


def test_tool_config_file_outside_working_directory_refused(tmp_path, job_directory):
    for filename in _escaping_filenames(tmp_path, job_directory):
        config_file = XmlTemplateConfigFile(name="script", filename=filename, content="echo hi")
        evaluator = _evaluator(ToolEvaluator, job_directory, config_file)
        with pytest.raises(RequestParameterInvalidException):
            evaluator._build_config_files()
    assert sorted(os.listdir(job_directory)) == ["configs", "working"]
    assert not (tmp_path / "elsewhere" / "x").exists()

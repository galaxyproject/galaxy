import abc
import os
from contextlib import contextmanager
from typing import (
    cast,
    Dict,
    Type,
)

from galaxy.app_unittest_utils.tools_support import (
    MockContext,
    UsesApp,
)
from galaxy.jobs import (
    JobWrapper,
    TaskWrapper,
)
from galaxy.model import (
    Base,
    Job,
    Task,
    User,
)
from galaxy.objectstore import BaseObjectStore
from galaxy.tools import ToolBox
from galaxy.util.bunch import Bunch
from galaxy.util.unittest import TestCase

TEST_TOOL_ID = "cufftest"
TEST_VERSION_COMMAND = "bwa --version"
TEST_DEPENDENCIES_COMMANDS = ". /galaxy/modules/bwa/0.5.9/env.sh"
TEST_COMMAND = ""


class AbstractTestCases:
    """Test classes that should not be collected.

    Classes derived from unittest.TestCase are collected only if they are at the
    module level: https://stackoverflow.com/a/25695512/4503125

    This workaround is needed because unittest/pytest try to collect test
    classes even if they are abstract, and therefore their tests fails.
    """

    class BaseWrapperTestCase(TestCase, UsesApp):
        def setUp(self):
            self.setup_app()
            job = Job()
            job.id = 345
            job.tool_id = TEST_TOOL_ID
            job.user = User()
            job.object_store_id = "foo"
            self.model_objects: Dict[Type[Base], Dict[int, Base]] = {Job: {345: job}}
            self.app.model.session = MockContext(self.model_objects)

            self.app._toolbox = cast(ToolBox, MockToolbox(MockTool(self)))
            self.working_directory = os.path.join(self.test_directory, "working")
            self.app.object_store = cast(BaseObjectStore, MockObjectStore(self.working_directory))

            self.queue = MockJobQueue(self.app)
            self.job = job

        def tearDown(self):
            self.tear_down_app()

        @contextmanager
        def _prepared_wrapper(self):
            wrapper = self._wrapper()
            wrapper._get_tool_evaluator = lambda *args, **kwargs: MockEvaluator(wrapper.app, wrapper.tool, wrapper.get_job(), wrapper.working_directory)  # type: ignore[method-assign]
            wrapper.prepare()
            yield wrapper

        def test_version_path(self):
            wrapper = self._wrapper()
            version_path = wrapper.get_version_string_path()
            expected_path = os.path.join(self.working_directory, "outputs", "COMMAND_VERSION")
            assert version_path == expected_path

        def test_prepare_sets_command_line(self):
            with self._prepared_wrapper() as wrapper:
                assert TEST_COMMAND in wrapper.command_line

        def test_prepare_sets_dependency_shell_commands(self):
            with self._prepared_wrapper() as wrapper:
                assert TEST_DEPENDENCIES_COMMANDS == wrapper.dependency_shell_commands

        @abc.abstractmethod
        def _wrapper(self) -> JobWrapper:
            pass


class TestJobWrapper(AbstractTestCases.BaseWrapperTestCase):
    def _wrapper(self):
        return JobWrapper(self.job, self.queue)  # type: ignore[arg-type]


class TestTaskWrapper(AbstractTestCases.BaseWrapperTestCase):
    def setUp(self):
        super().setUp()
        self.task = Task(self.job, self.working_directory, "prepare_bwa_job.sh")
        self.task.id = 4
        self.model_objects[Task] = {4: self.task}

    def _wrapper(self):
        return TaskWrapper(self.task, self.queue)


class MockEvaluator:
    def __init__(self, app, tool, job, local_working_directory):
        self.app = app
        self.tool = tool
        self.job = job
        self.local_working_directory = local_working_directory
        self.param_dict = {}

    def set_compute_environment(self, *args, **kwds):
        pass

    def build(self):
        return TEST_COMMAND, "", [], [], []


class MockJobQueue:
    def __init__(self, app):
        self.app = app
        self.dispatcher = MockJobDispatcher(app)


class MockJobDispatcher:
    def __init__(self, app):
        pass

    def url_to_destination(self):
        pass


class MockTool:
    def __init__(self, app):
        self.version_string_cmd = TEST_VERSION_COMMAND
        self.tool_dir = "/path/to/tools"
        self.dependencies = []
        self.requires_galaxy_python_environment = False
        self.id = "mock_id"
        self.home_target = None
        self.tmp_target = None
        self.tool_source = Bunch(to_string=lambda: "")

    def get_job_destination(self, params):
        return Bunch(runner="local", id="local", params={})

    def build_dependency_shell_commands(self, job_directory):
        return TEST_DEPENDENCIES_COMMANDS


class MockToolbox:
    def __init__(self, test_tool):
        self.test_tool = test_tool

    def get(self, tool_id, default=None):
        assert tool_id == TEST_TOOL_ID
        return self.test_tool

    def get_tool(self, tool_id, tool_version, exact=False):
        tool = self.get(tool_id)
        return tool


class MockObjectStore:
    def __init__(self, working_directory):
        self.working_directory = working_directory
        os.makedirs(working_directory)

    def create(self, *args, **kwds):
        pass

    def exists(self, *args, **kwargs):
        return True

    def construct_path(self, *args, **kwds):
        return self.working_directory

    def get_filename(self, *args, **kwds):
        if kwds.get("base_dir", "") == "job_work":
            return self.working_directory
        return None

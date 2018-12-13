import os
from contextlib import contextmanager
from unittest import TestCase

from galaxy.jobs import (
    JobWrapper,
    TaskWrapper
)
from galaxy.model import (
    Job,
    Task,
    User
)
from galaxy.tools import evaluation
from galaxy.util.bunch import Bunch
from ..tools_support import UsesApp

TEST_TOOL_ID = "cufftest"
TEST_VERSION_COMMAND = "bwa --version"
TEST_DEPENDENCIES_COMMANDS = ". /galaxy/modules/bwa/0.5.9/env.sh"
TEST_COMMAND = ""


class BaseWrapperTestCase(UsesApp):

    def setUp(self):
        self.setup_app()
        job = Job()
        job.id = 345
        job.tool_id = TEST_TOOL_ID
        job.user = User()
        job.object_store_id = "foo"
        self.model_objects = {Job: {345: job}}
        self.app.model.context = MockContext(self.model_objects)

        self.app.toolbox = MockToolbox(MockTool(self))
        self.working_directory = os.path.join(self.test_directory, "working")
        self.app.object_store = MockObjectStore(self.working_directory)

        self.queue = MockJobQueue(self.app)
        self.job = job

    def tearDown(self):
        self.tear_down_app()

    @contextmanager
    def _prepared_wrapper(self):
        wrapper = self._wrapper()
        with _mock_tool_evaluator(MockEvaluator):
            wrapper.prepare()
            yield wrapper

    def test_version_path(self):
        wrapper = self._wrapper()
        version_path = wrapper.get_version_string_path_legacy()
        expected_path = os.path.join(self.test_directory, "new_files", "GALAXY_VERSION_STRING_345")
        self.assertEqual(version_path, expected_path)

    def test_prepare_sets_command_line(self):
        with self._prepared_wrapper() as wrapper:
            assert TEST_COMMAND in wrapper.command_line

    def test_prepare_sets_dependency_shell_commands(self):
        with self._prepared_wrapper() as wrapper:
            assert TEST_DEPENDENCIES_COMMANDS == wrapper.dependency_shell_commands


class JobWrapperTestCase(BaseWrapperTestCase, TestCase):

    def _wrapper(self):
        return JobWrapper(self.job, self.queue)

    def test_prepare_sets_version_command(self):
        with self._prepared_wrapper() as wrapper:
            assert TEST_VERSION_COMMAND in wrapper.write_version_cmd, wrapper.write_version_cmd


class TaskWrapperTestCase(BaseWrapperTestCase, TestCase):

    def setUp(self):
        super(TaskWrapperTestCase, self).setUp()
        self.task = Task(self.job, self.working_directory, "prepare_bwa_job.sh")
        self.task.id = 4
        self.model_objects[Task] = {4: self.task}

    def _wrapper(self):
        return TaskWrapper(self.task, self.queue)

    def test_prepare_sets_no_version_command(self):
        with self._prepared_wrapper() as wrapper:
            assert wrapper.write_version_cmd is None


class MockEvaluator(object):

    def __init__(self, app, tool, job, local_working_directory):
        self.app = app
        self.tool = tool
        self.job = job
        self.local_working_directory = local_working_directory
        self.param_dict = {}

    def set_compute_environment(self, *args, **kwds):
        pass

    def build(self):
        return TEST_COMMAND, [], []


class MockJobQueue(object):

    def __init__(self, app):
        self.app = app
        self.dispatcher = MockJobDispatcher(app)


class MockJobDispatcher(object):

    def __init__(self, app):
        pass

    def url_to_destination(self):
        pass


class MockContext(object):

    def __init__(self, model_objects):
        self.expunged_all = False
        self.flushed = False
        self.model_objects = model_objects
        self.created_objects = []

    def expunge_all(self):
        self.expunged_all = True

    def query(self, clazz):
        return MockQuery(self.model_objects.get(clazz))

    def flush(self):
        self.flushed = True

    def add(self, object):
        self.created_objects.append(object)


class MockQuery(object):

    def __init__(self, class_objects):
        self.class_objects = class_objects

    def filter_by(self, **kwds):
        return Bunch(first=lambda: None)

    def get(self, id):
        return self.class_objects.get(id, None)


class MockTool(object):

    def __init__(self, app):
        self.version_string_cmd = TEST_VERSION_COMMAND
        self.tool_dir = "/path/to/tools"
        self.dependencies = []
        self.requires_galaxy_python_environment = False

    def build_dependency_shell_commands(self, job_directory):
        return TEST_DEPENDENCIES_COMMANDS


class MockToolbox(object):

    def __init__(self, test_tool):
        self.test_tool = test_tool

    def get(self, tool_id, default=None):
        assert tool_id == TEST_TOOL_ID
        return self.test_tool

    def get_tool(self, tool_id, tool_version, exact=False):
        tool = self.get(tool_id)
        return tool


class MockObjectStore(object):

    def __init__(self, working_directory):
        self.working_directory = working_directory
        os.makedirs(working_directory)

    def create(self, *args, **kwds):
        pass

    def get_filename(self, *args, **kwds):
        if kwds.get("base_dir", "") == "job_work":
            return self.working_directory
        return None


# Poor man's mocking. Need to get a real mocking library as real Galaxy development
# dependnecy.
@contextmanager
def _mock_tool_evaluator(mock_constructor):
    name = evaluation.ToolEvaluator.__name__
    real_classs = getattr(evaluation, name)
    try:
        setattr(evaluation, name, mock_constructor)
        yield
    finally:
        setattr(evaluation, name, real_classs)

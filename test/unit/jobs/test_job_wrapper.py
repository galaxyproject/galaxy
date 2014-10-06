import os
from contextlib import contextmanager

from unittest import TestCase
from galaxy.model import Job
from galaxy.model import Task
from galaxy.model import User
from galaxy.jobs import JobWrapper
from galaxy.jobs import TaskWrapper
from galaxy.util.bunch import Bunch

from galaxy.tools import evaluation

from tools_support import UsesApp
#from tools_support import MockTool

#from ..tools_and_jobs_helpers import MockApp

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
        version_path = wrapper.get_version_string_path()
        expected_path = os.path.join(self.test_directory, "new_files", "GALAXY_VERSION_STRING_345")
        self.assertEquals(version_path, expected_path)

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
        return TEST_COMMAND, []


class MockJobQueue(object):

    def __init__(self, app):
        self.app = app
        self.dispatcher = MockJobDispatcher(app)


class MockJobDispatcher(object):

    def __init__(self, app):
        pass

    def url_to_destination(self):
        pass


class MockApp(object):

    def __init__(self, object_store, test_directory, model_objects):
        self.object_store = object_store
        self.toolbox = MockToolbox(MockTool(self))
        self.config = Bunch(
            outputs_to_working_directory=False,
            new_file_path=os.path.join(test_directory, "new_files"),
            tool_data_path=os.path.join(test_directory, "tools"),
            root=os.path.join(test_directory, "galaxy"),
            datatypes_registry=Bunch(
                integrated_datatypes_configs=os.path.join(test_directory, "datatypes_conf.xml"),
            ),
        )
        self.job_config = Bunch(
            dynamic_params=None,
        )
        self.model = Bunch(context=MockContext(model_objects))


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

    def build_dependency_shell_commands(self):
        return TEST_DEPENDENCIES_COMMANDS


class MockToolbox(object):

    def __init__(self, test_tool):
        self.test_tool = test_tool

    @property
    def tools_by_id(self):
        return self

    def get(self, tool_id, default=None):
        assert tool_id == TEST_TOOL_ID
        return self.test_tool


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


## Poor man's mocking. Need to get a real mocking library as real Galaxy development
## dependnecy.
@contextmanager
def _mock_tool_evaluator(mock_constructor):
    name = evaluation.ToolEvaluator.__name__
    real_classs = getattr(evaluation, name)
    try:
        setattr(evaluation, name, mock_constructor)
        yield
    finally:
        setattr(evaluation, name, real_classs)

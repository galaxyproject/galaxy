import abc
import os
from contextlib import contextmanager
from types import SimpleNamespace
from typing import (
    cast,
    TYPE_CHECKING,
)
from uuid import uuid4

from galaxy.app_unittest_utils.tools_support import (
    MockContext,
    UsesApp,
)
from galaxy.jobs import (
    JobWrapper,
    MinimalJobWrapper,
    TaskWrapper,
)
from galaxy.jobs.handler import BaseJobHandlerQueue
from galaxy.model import (
    Base,
    Job,
    Task,
    User,
)
from galaxy.objectstore import BaseObjectStore
from galaxy.tools import ToolBox
from galaxy.tools.parameters.basic import DirectoryUriToolParameter
from galaxy.util import XML
from galaxy.util.bunch import Bunch
from galaxy.util.unittest import TestCase

if TYPE_CHECKING:
    from sqlalchemy.orm import scoped_session

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
            self.model_objects: dict[type[Base], dict[int, Base]] = {Job: {345: job}}
            self.app.model.session = cast("scoped_session", MockContext(self.model_objects))

            self.app._toolbox = cast(ToolBox, MockToolbox(MockTool(self)))
            self.working_directory = os.path.join(self.test_directory, "working")
            self.app.object_store = cast(BaseObjectStore, MockObjectStore(self.working_directory))

            self.queue = cast(BaseJobHandlerQueue, MockJobQueue(self.app))
            self.job = job

        def tearDown(self):
            self.tear_down_app()

        @contextmanager
        def _prepared_wrapper(self):
            wrapper = self._wrapper()
            wrapper._get_tool_evaluator = lambda *args, **kwargs: MockEvaluator(  # type: ignore[method-assign]
                wrapper.app, wrapper.tool, wrapper.get_job(), wrapper.working_directory
            )
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
        return JobWrapper(self.job, self.queue)


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
        self.use_cached_job = False

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
        self.inputs = {}
        self.tool_action = SimpleNamespace(
            has_complete_file_source_uri_discovery=lambda: True,
            iter_referenced_file_source_uris=lambda param_dict: (),
        )

    def params_from_strings(self, param_dict):
        return param_dict

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

    def tool_for_job(self, job, exact, check_access=True, user=None):
        tool = self.get(job.tool_id)
        return tool

    def materialize_tool(self, tool, *, reason):
        assert reason == "job_setup"
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


def _minimal_wrapper(param_dict=None, inputs=None, action_uris=(), action_discovery_complete=True):
    tool_action = SimpleNamespace(
        has_complete_file_source_uri_discovery=lambda: action_discovery_complete,
        iter_referenced_file_source_uris=lambda param_dict: action_uris,
    )
    return SimpleNamespace(
        tool=SimpleNamespace(inputs=inputs or {}, tool_action=tool_action),
        get_param_dict=lambda job: param_dict or {},
    )


def _job_with_file_source_inputs(input_datasets=None, input_library_datasets=None):
    return SimpleNamespace(
        id=1,
        input_datasets=input_datasets or [],
        input_library_datasets=input_library_datasets or [],
    )


def test_referenced_file_source_uris_reads_tool_parameters_and_action():
    destination = "gxfiles://good/out"
    fetched = f"gxuserfiles://{uuid4().hex}/input"
    destination_param = DirectoryUriToolParameter(None, XML('<param name="destination" type="directory_uri"/>'))
    wrapper = _minimal_wrapper(
        param_dict={"destination": destination},
        inputs={"destination": destination_param},
        action_uris=(fetched,),
    )
    assert MinimalJobWrapper._referenced_file_source_uris(wrapper, _job_with_file_source_inputs()) == {
        destination,
        fetched,
    }


def test_referenced_file_source_uris_empty_for_job_without_sources():
    assert MinimalJobWrapper._referenced_file_source_uris(_minimal_wrapper(), _job_with_file_source_inputs()) == set()


def test_referenced_file_source_uris_unknown_for_unaudited_action():
    wrapper = _minimal_wrapper(action_discovery_complete=False)
    assert MinimalJobWrapper._referenced_file_source_uris(wrapper, _job_with_file_source_inputs()) is None


def test_referenced_file_source_uris_adds_regular_and_library_input_sources():
    regular_src = f"gxuserfiles://{uuid4().hex}/regular.txt"
    library_src = f"gxuserfiles://{uuid4().hex}/library.txt"
    hda = SimpleNamespace(has_deferred_data=True, dataset=SimpleNamespace(source_uris=[regular_src]))
    ldda = SimpleNamespace(has_deferred_data=True, dataset=SimpleNamespace(source_uris=[library_src]))
    job = _job_with_file_source_inputs(
        input_datasets=[SimpleNamespace(dataset=hda)],
        input_library_datasets=[SimpleNamespace(dataset=ldda)],
    )
    assert MinimalJobWrapper._referenced_file_source_uris(_minimal_wrapper(), job) == {regular_src, library_src}


def test_referenced_file_source_uris_ignores_materialized_input_sources():
    source = f"gxuserfiles://{uuid4().hex}/materialized.txt"
    hda = SimpleNamespace(has_deferred_data=False, dataset=SimpleNamespace(source_uris=[source]))
    job = _job_with_file_source_inputs(input_datasets=[SimpleNamespace(dataset=hda)])
    assert MinimalJobWrapper._referenced_file_source_uris(_minimal_wrapper(), job) == set()


def test_fix_output_permissions_does_not_initialize_job_io():
    class WrapperWithoutJobIO:
        _job_io = None

        @property
        def job_io(self):
            raise AssertionError("job_io should not be initialized during failure cleanup")

    wrapper = cast(MinimalJobWrapper, WrapperWithoutJobIO())
    MinimalJobWrapper._fix_output_permissions(wrapper)

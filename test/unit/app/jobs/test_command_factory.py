import os
import shutil
from os import getcwd
from tempfile import mkdtemp
from typing import (
    List,
    Tuple,
)

from galaxy.jobs.command_factory import (
    build_command,
    SETUP_GALAXY_FOR_METADATA,
)
from galaxy.tool_util.deps.container_classes import TRAP_KILL_CONTAINER
from galaxy.util.bunch import Bunch
from galaxy.util.unittest import TestCase

MOCK_COMMAND_LINE = "/opt/galaxy/tools/bowtie /mnt/galaxyData/files/000/input000.dat"
TEST_METADATA_LINE = "set_metadata_and_stuff.sh"
TEST_FILES_PATH = "file_path"
TEE_REDIRECT = '> "$__out" 2> "$__err"'
RETURN_CODE_CAPTURE = "; return_code=$?; echo $return_code > galaxy_1.ec"
CP_WORK_DIR_OUTPUTS = '; \nif [ -f "foo" -a -f "bar" ] ; then cp "foo" "bar" ; fi'


class TestCommandFactory(TestCase):
    maxDiff = None
    stream_stdout_stderr = False
    TEE_LOG = " "
    CAPTURE_AND_REDIRECT = f"> '../outputs/tool_stdout' 2> '../outputs/tool_stderr'{RETURN_CODE_CAPTURE}"

    def setUp(self):
        self.job_dir = mkdtemp()
        self.job_wrapper = MockJobWrapper(self.job_dir)
        self.workdir_outputs: List[Tuple[str, str]] = []

        def workdir_outputs(job_wrapper, **kwds):
            assert job_wrapper == self.job_wrapper
            return self.workdir_outputs

        self.runner = Bunch(
            app=Bunch(model=Bunch(Dataset=Bunch(file_path=TEST_FILES_PATH))), get_work_dir_outputs=workdir_outputs
        )
        self.include_metadata = False
        self.include_work_dir_outputs = True

    def tearDown(self):
        shutil.rmtree(self.job_dir)

    def test_simplest_command(self):
        self.include_work_dir_outputs = False
        self._assert_command_is(self._surround_command(MOCK_COMMAND_LINE))

    def test_shell_commands(self):
        self.include_work_dir_outputs = False
        dep_commands = [". /opt/galaxy/tools/bowtie/default/env.sh"]
        self.job_wrapper.dependency_shell_commands = dep_commands
        self._assert_command_is(self._surround_command(f"{dep_commands[0]}; {MOCK_COMMAND_LINE}"))

    def test_shell_commands_external(self):
        self.job_wrapper.commands_in_new_shell = True
        self.include_work_dir_outputs = False
        dep_commands = [". /opt/galaxy/tools/bowtie/default/env.sh"]
        self.job_wrapper.dependency_shell_commands = dep_commands
        self._assert_command_is(
            self._surround_command(f"{self.job_wrapper.shell} {self.job_wrapper.working_directory}/tool_script.sh")
        )
        self.__assert_tool_script_is(f"#!/bin/sh\n{dep_commands[0]}; {MOCK_COMMAND_LINE}")

    def test_remote_dependency_resolution(self):
        self.include_work_dir_outputs = False
        dep_commands = [". /opt/galaxy/tools/bowtie/default/env.sh"]
        self.job_wrapper.dependency_shell_commands = dep_commands
        self._assert_command_is(
            self._surround_command(MOCK_COMMAND_LINE), remote_command_params=dict(dependency_resolution="remote")
        )

    def test_explicit_local_dependency_resolution(self):
        self.include_work_dir_outputs = False
        dep_commands = [". /opt/galaxy/tools/bowtie/default/env.sh"]
        self.job_wrapper.dependency_shell_commands = dep_commands
        self._assert_command_is(
            self._surround_command(f"{dep_commands[0]}; {MOCK_COMMAND_LINE}"),
            remote_command_params=dict(dependency_resolution="local"),
        )

    def test_task_prepare_inputs(self):
        self.include_work_dir_outputs = False
        self.job_wrapper.prepare_input_files_cmds = ["/opt/split1", "/opt/split2"]
        self._assert_command_is(self._surround_command(f"/opt/split1; /opt/split2; {MOCK_COMMAND_LINE}"))

    def test_workdir_outputs(self):
        self.include_work_dir_outputs = True
        self.workdir_outputs = [("foo", "bar")]
        self._assert_command_is(self._surround_command(MOCK_COMMAND_LINE, CP_WORK_DIR_OUTPUTS))

    def test_workdir_outputs_with_glob(self):
        self.include_work_dir_outputs = True
        self.workdir_outputs = [("foo*bar", "foo_x_bar")]
        self._assert_command_is(
            self._surround_command(
                MOCK_COMMAND_LINE, '; \nif [ -f "foo"*"bar" -a -f "foo_x_bar" ] ; then cp "foo"*"bar" "foo_x_bar" ; fi'
            )
        )

    def test_set_metadata_skipped_if_unneeded(self):
        self.include_metadata = True
        self.include_work_dir_outputs = False
        self._assert_command_is(self._surround_command(MOCK_COMMAND_LINE))

    def test_set_metadata(self):
        self._test_set_metadata()

    def test_strips_trailing_semicolons(self):
        self.job_wrapper.command_line = f"{MOCK_COMMAND_LINE};"
        self._test_set_metadata()

    def _test_set_metadata(self):
        self.include_metadata = True
        self.include_work_dir_outputs = False
        self.job_wrapper.metadata_line = TEST_METADATA_LINE
        expected_command = self._surround_command(
            MOCK_COMMAND_LINE, f"; cd '{self.job_dir}'; {SETUP_GALAXY_FOR_METADATA}; {TEST_METADATA_LINE}"
        )
        self._assert_command_is(expected_command)

    def test_empty_metadata(self):
        """
        Test empty metadata as produced by TaskWrapper.
        """
        self.include_metadata = True
        self.include_work_dir_outputs = False
        self.job_wrapper.metadata_line = " "
        # Empty metadata command do not touch command line.
        expected_command = self._surround_command(MOCK_COMMAND_LINE, f"; cd '{self.job_dir}'")
        self._assert_command_is(expected_command)

    def test_metadata_kwd_defaults(self):
        configured_kwds = self.__set_metadata_with_kwds()
        assert configured_kwds["exec_dir"] == getcwd()
        assert configured_kwds["tmp_dir"] == self.job_wrapper.working_directory
        assert configured_kwds["dataset_files_path"] == TEST_FILES_PATH
        assert configured_kwds["output_fnames"] == ["output1"]

    def test_metadata_kwds_overrride(self):
        configured_kwds = self.__set_metadata_with_kwds(
            exec_dir="/path/to/remote/galaxy",
            tmp_dir="/path/to/remote/staging/directory/job1",
            dataset_files_path="/path/to/remote/datasets/",
            output_fnames=["/path/to/remote_output1"],
        )
        assert configured_kwds["exec_dir"] == "/path/to/remote/galaxy"
        assert configured_kwds["tmp_dir"] == "/path/to/remote/staging/directory/job1"
        assert configured_kwds["dataset_files_path"] == "/path/to/remote/datasets/"
        assert configured_kwds["output_fnames"] == ["/path/to/remote_output1"]

    def __set_metadata_with_kwds(self, **kwds):
        self.include_metadata = True
        self.include_work_dir_outputs = False
        self.job_wrapper.metadata_line = TEST_METADATA_LINE
        if kwds:
            self.__command(remote_command_params=dict(metadata_kwds=kwds))
        else:
            self.__command()
        return self.job_wrapper.configured_external_metadata_kwds

    def _assert_command_is(self, expected_command, **command_kwds):
        command = self.__command(**command_kwds)
        assert command == expected_command

    def __assert_tool_script_is(self, expected_command):
        assert open(self.__tool_script).read() == expected_command

    @property
    def __tool_script(self):
        return os.path.join(self.job_dir, "tool_script.sh")

    def __command(self, **extra_kwds):
        kwds = dict(
            runner=self.runner,
            job_wrapper=self.job_wrapper,
            include_metadata=self.include_metadata,
            include_work_dir_outputs=self.include_work_dir_outputs,
            stream_stdout_stderr=self.stream_stdout_stderr,
            **extra_kwds,
        )
        return build_command(**kwds)

    def _surround_command(self, command, post_command=""):
        command = f'''cd working;{self.TEE_LOG}{command} {self.CAPTURE_AND_REDIRECT}{post_command}; sh -c "exit $return_code"'''
        return command.replace("galaxy_1.ec", os.path.join(self.job_wrapper.working_directory, "galaxy_1.ec"), 1)


class TestCommandFactoryStreamStdoutStderr(TestCommandFactory):
    stream_stdout_stderr = True
    TEE_LOG = """ __out="${TMPDIR:-.}/out.$$" __err="${TMPDIR:-.}/err.$$"
mkfifo "$__out" "$__err"
trap 'rm -f "$__out" "$__err"' EXIT
tee -a '../outputs/tool_stdout' < "$__out" &
tee -a '../outputs/tool_stderr' < "$__err" >&2 & """
    CAPTURE_AND_REDIRECT = f"{TEE_REDIRECT}{RETURN_CODE_CAPTURE}"

    def test_kill_trap_replaced(self):
        self.include_work_dir_outputs = False
        self.job_wrapper.command_line = f"{TRAP_KILL_CONTAINER}{MOCK_COMMAND_LINE}"
        expected_command_line = self._surround_command(MOCK_COMMAND_LINE).replace(
            """trap 'rm -f "$__out" "$__err"' EXIT""", """trap 'rm -f "$__out" "$__err"; _on_exit' EXIT"""
        )
        self._assert_command_is(expected_command_line)


class MockJobWrapper:
    def __init__(self, job_dir):
        self.strict_shell = False
        self.command_line = MOCK_COMMAND_LINE
        self.dependency_shell_commands = []
        self.metadata_line = None
        self.configured_external_metadata_kwds = None
        self.working_directory = job_dir
        self.prepare_input_files_cmds = None
        self.commands_in_new_shell = False
        self.app = Bunch(
            config=Bunch(
                check_job_script_integrity=False,
            )
        )
        self.shell = "/bin/sh"
        self.use_metadata_binary = False
        self.job_id = 1
        self.remote_command_line = False

    def get_command_line(self):
        return self.command_line

    def container_monitor_command(self, *args, **kwds):
        return None

    @property
    def requires_setting_metadata(self):
        return self.metadata_line is not None

    def setup_external_metadata(self, *args, **kwds):
        self.configured_external_metadata_kwds = kwds
        return self.metadata_line

    @property
    def job_io(self):
        return Bunch(
            get_output_fnames=lambda: ["output1"],
            check_job_script_integrity=False,
            version_path=None,
        )

    @property
    def is_cwl_job(self):
        return False

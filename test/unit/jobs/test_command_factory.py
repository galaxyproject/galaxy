import os
import shutil
from os import getcwd
from tempfile import mkdtemp
from unittest import TestCase

from galaxy.jobs.command_factory import build_command, SETUP_GALAXY_FOR_METADATA
from galaxy.util.bunch import Bunch

MOCK_COMMAND_LINE = "/opt/galaxy/tools/bowtie /mnt/galaxyData/files/000/input000.dat"
TEST_METADATA_LINE = "set_metadata_and_stuff.sh"
TEST_FILES_PATH = "file_path"


class TestCommandFactory(TestCase):

    def setUp(self):
        self.job_dir = mkdtemp()
        self.job_wrapper = MockJobWrapper(self.job_dir)
        self.workdir_outputs = []

        def workdir_outputs(job_wrapper, **kwds):
            assert job_wrapper == self.job_wrapper
            return self.workdir_outputs

        self.runner = Bunch(app=Bunch(model=Bunch(Dataset=Bunch(file_path=TEST_FILES_PATH))), get_work_dir_outputs=workdir_outputs)
        self.include_metadata = False
        self.include_work_dir_outputs = True

    def tearDown(self):
        shutil.rmtree(self.job_dir)

    def test_simplest_command(self):
        self.include_work_dir_outputs = False
        self.__assert_command_is(_surround_command(MOCK_COMMAND_LINE + "; return_code=$?"))

    def test_shell_commands(self):
        self.include_work_dir_outputs = False
        dep_commands = [". /opt/galaxy/tools/bowtie/default/env.sh"]
        self.job_wrapper.dependency_shell_commands = dep_commands
        self.__assert_command_is(_surround_command("%s; %s; return_code=$?" % (dep_commands[0], MOCK_COMMAND_LINE)))

    def test_shell_commands_external(self):
        self.job_wrapper.commands_in_new_shell = True
        self.include_work_dir_outputs = False
        dep_commands = [". /opt/galaxy/tools/bowtie/default/env.sh"]
        self.job_wrapper.dependency_shell_commands = dep_commands
        self.__assert_command_is(_surround_command("%s/tool_script.sh; return_code=$?" % self.job_wrapper.working_directory))
        self.__assert_tool_script_is("#!/bin/sh\n%s; %s" % (dep_commands[0], MOCK_COMMAND_LINE))

    def test_remote_dependency_resolution(self):
        self.include_work_dir_outputs = False
        dep_commands = [". /opt/galaxy/tools/bowtie/default/env.sh"]
        self.job_wrapper.dependency_shell_commands = dep_commands
        self.__assert_command_is(_surround_command(MOCK_COMMAND_LINE + "; return_code=$?"), remote_command_params=dict(dependency_resolution="remote"))

    def test_explicit_local_dependency_resolution(self):
        self.include_work_dir_outputs = False
        dep_commands = [". /opt/galaxy/tools/bowtie/default/env.sh"]
        self.job_wrapper.dependency_shell_commands = dep_commands
        self.__assert_command_is(_surround_command("%s; %s; return_code=$?" % (dep_commands[0], MOCK_COMMAND_LINE)),
                                 remote_command_params=dict(dependency_resolution="local"))

    def test_task_prepare_inputs(self):
        self.include_work_dir_outputs = False
        self.job_wrapper.prepare_input_files_cmds = ["/opt/split1", "/opt/split2"]
        self.__assert_command_is(_surround_command("/opt/split1; /opt/split2; %s; return_code=$?") % MOCK_COMMAND_LINE)

    def test_workdir_outputs(self):
        self.include_work_dir_outputs = True
        self.workdir_outputs = [("foo", "bar")]
        self.__assert_command_is(_surround_command('%s; return_code=$?; if [ -f foo ] ; then cp foo bar ; fi' % MOCK_COMMAND_LINE))

    def test_set_metadata_skipped_if_unneeded(self):
        self.include_metadata = True
        self.include_work_dir_outputs = False
        self.__assert_command_is(_surround_command(MOCK_COMMAND_LINE + "; return_code=$?"))

    def test_set_metadata(self):
        self._test_set_metadata()

    def test_strips_trailing_semicolons(self):
        self.job_wrapper.command_line = "%s;" % MOCK_COMMAND_LINE
        self._test_set_metadata()

    def _test_set_metadata(self):
        self.include_metadata = True
        self.include_work_dir_outputs = False
        self.job_wrapper.metadata_line = TEST_METADATA_LINE
        expected_command = _surround_command("%s; return_code=$?; cd '%s'; %s%s" % (MOCK_COMMAND_LINE, self.job_dir, SETUP_GALAXY_FOR_METADATA, TEST_METADATA_LINE))
        self.__assert_command_is(expected_command)

    def test_empty_metadata(self):
        """
        Test empty metadata as produced by TaskWrapper.
        """
        self.include_metadata = True
        self.include_work_dir_outputs = False
        self.job_wrapper.metadata_line = ' '
        # Empty metadata command do not touch command line.
        expected_command = _surround_command("%s; return_code=$?; cd '%s'" % (MOCK_COMMAND_LINE, self.job_dir))
        self.__assert_command_is(expected_command)

    def test_metadata_kwd_defaults(self):
        configured_kwds = self.__set_metadata_with_kwds()
        assert configured_kwds['exec_dir'] == getcwd()
        assert configured_kwds['tmp_dir'] == self.job_wrapper.working_directory
        assert configured_kwds['dataset_files_path'] == TEST_FILES_PATH
        assert configured_kwds['output_fnames'] == ['output1']

    def test_metadata_kwds_overrride(self):
        configured_kwds = self.__set_metadata_with_kwds(
            exec_dir="/path/to/remote/galaxy",
            tmp_dir="/path/to/remote/staging/directory/job1",
            dataset_files_path="/path/to/remote/datasets/",
            output_fnames=['/path/to/remote_output1'],
        )
        assert configured_kwds['exec_dir'] == "/path/to/remote/galaxy"
        assert configured_kwds['tmp_dir'] == "/path/to/remote/staging/directory/job1"
        assert configured_kwds['dataset_files_path'] == "/path/to/remote/datasets/"
        assert configured_kwds['output_fnames'] == ['/path/to/remote_output1']

    def __set_metadata_with_kwds(self, **kwds):
        self.include_metadata = True
        self.include_work_dir_outputs = False
        self.job_wrapper.metadata_line = TEST_METADATA_LINE
        if kwds:
            self.__command(remote_command_params=dict(metadata_kwds=kwds))
        else:
            self.__command()
        return self.job_wrapper.configured_external_metadata_kwds

    def __assert_command_is(self, expected_command, **command_kwds):
        command = self.__command(**command_kwds)
        self.assertEqual(command, expected_command)

    def __assert_tool_script_is(self, expected_command):
        self.assertEqual(open(self.__tool_script, "r").read(), expected_command)

    @property
    def __tool_script(self):
        return os.path.join(self.job_dir, "tool_script.sh")

    def __command(self, **extra_kwds):
        kwds = dict(
            runner=self.runner,
            job_wrapper=self.job_wrapper,
            include_metadata=self.include_metadata,
            include_work_dir_outputs=self.include_work_dir_outputs,
            **extra_kwds
        )
        return build_command(**kwds)


def _surround_command(command):
    return '''rm -rf working; mkdir -p working; cd working; %s; sh -c "exit $return_code"''' % command


class MockJobWrapper(object):

    def __init__(self, job_dir):
        self.strict_shell = False
        self.write_version_cmd = None
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

    def get_command_line(self):
        return self.command_line

    @property
    def requires_setting_metadata(self):
        return self.metadata_line is not None

    def setup_external_metadata(self, *args, **kwds):
        self.configured_external_metadata_kwds = kwds
        return self.metadata_line

    def get_output_fnames(self):
        return ["output1"]

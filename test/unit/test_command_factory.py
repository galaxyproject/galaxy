from os import getcwd
from unittest import TestCase

from galaxy.jobs.command_factory import build_command
from galaxy.util.bunch import Bunch

MOCK_COMMAND_LINE = "/opt/galaxy/tools/bowtie /mnt/galaxyData/files/000/input000.dat"


class TestCommandFactory(TestCase):

    def setUp(self):
        self.job_wrapper = MockJobWrapper()
        self.job = Bunch(app=Bunch(model=Bunch(Dataset=Bunch(file_path="file_path"))))
        self.include_metadata = False
        self.include_work_dir_outputs = True

    def test_simplest_command(self):
        self.include_work_dir_outputs = False
        self.__assert_command_is( MOCK_COMMAND_LINE )

    def test_shell_commands(self):
        self.include_work_dir_outputs = False
        dep_commands = [". /opt/galaxy/tools/bowtie/default/env.sh"]
        self.job_wrapper.dependency_shell_commands = dep_commands
        self.__assert_command_is( "%s; %s" % (dep_commands[0], MOCK_COMMAND_LINE) )

    def test_set_metadata_skipped_if_unneeded(self):
        self.include_metadata = True
        self.include_work_dir_outputs = False
        self.__assert_command_is( MOCK_COMMAND_LINE )

    def test_set_metadata(self):
        self._test_set_metadata()

    def test_strips_trailing_semicolons(self):
        self.job_wrapper.command_line = "%s;" % MOCK_COMMAND_LINE
        self._test_set_metadata()

    def _test_set_metadata(self):
        self.include_metadata = True
        self.include_work_dir_outputs = False
        metadata_line = "set_metadata_and_stuff.sh"
        self.job_wrapper.metadata_line = metadata_line
        expected_command = '%s; return_code=$?; cd %s; %s; sh -c "exit $return_code"' % (MOCK_COMMAND_LINE, getcwd(), metadata_line)
        self.__assert_command_is( expected_command )

    def test_empty_metadata(self):
        """
        As produced by TaskWrapper.
        """
        self.include_metadata = True
        self.include_work_dir_outputs = False
        self.job_wrapper.metadata_line = ' '
        # Empty metadata command do not touch command line.
        expected_command = '%s' % (MOCK_COMMAND_LINE)
        self.__assert_command_is( expected_command )
        
        
    def __assert_command_is(self, expected_command):
        command = self.__command()
        self.assertEqual(command, expected_command)

    def __command(self):
        kwds = dict(
            job=self.job,
            job_wrapper=self.job_wrapper,
            include_metadata=self.include_metadata,
            include_work_dir_outputs=self.include_work_dir_outputs,
        )
        return build_command(**kwds)


class MockJobWrapper(object):

    def __init__(self):
        self.version_string_cmd = None
        self.command_line = MOCK_COMMAND_LINE
        self.dependency_shell_commands = []
        self.metadata_line = None
        self.working_directory = "job1"

    def get_command_line(self):
        return self.command_line

    @property
    def requires_setting_metadata(self):
        return self.metadata_line is not None

    def setup_external_metadata(self, *args, **kwds):
        return self.metadata_line

    def get_output_fnames(self):
        return []


class MockJob(object):
    app = Bunch()

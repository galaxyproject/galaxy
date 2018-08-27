from unittest import TestCase

from galaxy.jobs.output_checker import check_output, DETECTED_JOB_STATE
from galaxy.model import Job
from galaxy.tools.parser.error_level import StdioErrorLevel
from galaxy.tools.parser.interface import ToolStdioRegex
from galaxy.util.bunch import Bunch


class OutputCheckerTestCase(TestCase):

    def setUp(self):
        self.tool = Bunch(
            stdio_regexes=[],
            stdio_exit_codes=[],
        )
        self.job = Job()
        self.job.id = "test_id"
        self.stdout = ''
        self.stderr = ''
        self.tool_exit_code = None

    def test_default_no_stderr_success(self):
        self.__assertSuccessful()

    def test_default_stderr_failure(self):
        self.stderr = 'foo'
        self.__assertNotSuccessful()

    def test_exit_code_error(self):
        mock_exit_code = Bunch(range_start=1, range_end=1, error_level=StdioErrorLevel.FATAL, desc=None)
        self.tool.stdio_exit_codes.append(mock_exit_code)
        self.tool_exit_code = 1
        self.__assertNotSuccessful()

    def test_exit_code_success(self):
        mock_exit_code = Bunch(range_start=1, range_end=1, error_level=StdioErrorLevel.FATAL, desc=None)
        self.tool.stdio_exit_codes.append(mock_exit_code)
        self.tool_exit_code = 0
        self.__assertSuccessful()

    def test_problematic_strings_matching(self):
        problematic_str = '\x80abc'
        self.__add_regex(Bunch(match=r'.abc', stdout_match=False, stderr_match=True, error_level=StdioErrorLevel.FATAL, desc=None))
        self.stderr = problematic_str
        self.__assertNotSuccessful()

    def test_problematic_strings_not_matching(self):
        problematic_str = '\x80abc'
        self.__add_regex(Bunch(match=r'.abcd', stdout_match=False, stderr_match=True, error_level=StdioErrorLevel.FATAL, desc=None))
        self.stderr = problematic_str
        self.__assertSuccessful()

    def test_stderr_regex_negative_match(self):
        regex = ToolStdioRegex()
        regex.stderr_match = True
        regex.match = "foobar"
        self.__add_regex(regex)
        self.stderr = "foo"
        self.__assertSuccessful()

    def test_stderr_regex_positive_match(self):
        regex = ToolStdioRegex()
        regex.stderr_match = True
        regex.match = "foo"
        self.__add_regex(regex)
        self.stderr = "foobar"
        self.__assertNotSuccessful()

    def test_stdout_ignored_for_stderr_regexes(self):
        regex = ToolStdioRegex()
        regex.stderr_match = True
        regex.match = "foo"
        self.__add_regex(regex)
        self.stdout = "foobar"
        self.__assertSuccessful()

    def test_stderr_ignored_for_stdout_regexes(self):
        regex = ToolStdioRegex()
        regex.stdout_match = True
        regex.match = "foo"
        self.__add_regex(regex)
        self.stderr = "foobar"
        self.__assertSuccessful()

    def __add_regex(self, regex):
        self.tool.stdio_regexes.append(regex)

    def __assertSuccessful(self):
        assert self.__check_output() == DETECTED_JOB_STATE.OK

    def __assertNotSuccessful(self):
        assert self.__check_output() != DETECTED_JOB_STATE.OK

    def __check_output(self):
        return check_output(self.tool, self.stdout, self.stderr, self.tool_exit_code, self.job)

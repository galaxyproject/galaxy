import os
from pathlib import Path

from .test_parsing import BaseLoaderTestCase

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
TEST_TOOL_DIRECTORIES = os.path.join(SCRIPT_DIRECTORY, "tool_directories")


TOOL_REQUIRED_FILES_XML_1 = """
<tool name="required_files_1" id="required_files_1" version="0.1.0">
    <command>foo</command>
    <required_files>
        <include path="my_script.R" />
    </required_files>
    <inputs>
        <input type="text" label="Text to parse." name="input1" />
    </inputs>
    <outputs>
        <output type="integer" name="out1" from="output" />
    </outputs>
</tool>
"""


TOOL_REQUIRED_FILES_XML_2 = """
<tool name="required_files_1" id="required_files_1" version="0.1.0">
    <command>foo</command>
    <required_files>
        <include path="*.R" type="glob" />
        <exclude path="other_script.R" />
    </required_files>
    <inputs>
        <input type="text" label="Text to parse." name="input1" />
    </inputs>
    <outputs>
        <output type="integer" name="out1" from="output" />
    </outputs>
</tool>
"""


TOOL_REQUIRED_FILES_XML_3 = """
<tool name="required_files_1" id="required_files_1" version="0.1.0">
    <command>foo</command>
    <required_files>
        <include path="*.R" type="glob" />
    </required_files>
    <inputs>
        <input type="text" label="Text to parse." name="input1" />
    </inputs>
    <outputs>
        <output type="integer" name="out1" from="output" />
    </outputs>
</tool>
"""


TOOL_REQUIRED_FILES_XML_4 = """
<tool name="required_files_1" id="required_files_1" version="0.1.0">
    <command>foo</command>
    <required_files>
        <include path=".*R" type="regex" />
        <exclude path="other_script*" type="glob" />
    </required_files>
    <inputs>
        <input type="text" label="Text to parse." name="input1" />
    </inputs>
    <outputs>
        <output type="integer" name="out1" from="output" />
    </outputs>
</tool>
"""


TOOL_REQUIRED_FILES_XML_DISABLED_DEFAULT_EXCLUSIONS = """
<tool name="required_files_1" id="required_files_1" version="0.1.0">
    <command>foo</command>
    <required_files extend_default_excludes="false">
        <include path="*.R" type="glob" />
    </required_files>
    <inputs>
        <input type="text" label="Text to parse." name="input1" />
    </inputs>
    <outputs>
        <output type="integer" name="out1" from="output" />
    </outputs>
</tool>
"""


class BaseRequiredFilesTestCase(BaseLoaderTestCase):
    source_file_name = "required_files.xml"

    def _required_files(self, tool_directory: str):
        tool_source = self._tool_source
        required_files = tool_source.parse_required_files()
        return required_files.find_required_files(tool_directory)


# directly include just one file that is there
class RequiredFiles1TestCase(BaseRequiredFilesTestCase):
    source_contents = TOOL_REQUIRED_FILES_XML_1

    def test_expected_files(self):
        files = self._required_files(os.path.join(TEST_TOOL_DIRECTORIES, "r-tool-dir"))
        assert len(files) == 1
        assert "my_script.R" in files


# include a glob and exclude a file in the glob
class RequiredFiles2TestCase(BaseRequiredFilesTestCase):
    source_contents = TOOL_REQUIRED_FILES_XML_2

    def test_expected_files(self):
        files = self._required_files(os.path.join(TEST_TOOL_DIRECTORIES, "r-tool-dir"))
        assert len(files) == 1
        assert "my_script.R" in files


# include a glob with multiple matches
class RequiredFiles3TestCase(BaseRequiredFilesTestCase):
    source_contents = TOOL_REQUIRED_FILES_XML_3

    def test_expected_files(self):
        files = self._required_files(os.path.join(TEST_TOOL_DIRECTORIES, "r-tool-dir"))
        assert len(files) == 2
        assert "my_script.R" in files
        assert "other_script.R" in files


# include a file with regex and exclude with glob
class RequiredFiles4TestCase(BaseRequiredFilesTestCase):
    source_contents = TOOL_REQUIRED_FILES_XML_4

    def test_expected_files(self):
        files = self._required_files(os.path.join(TEST_TOOL_DIRECTORIES, "r-tool-dir"))
        assert len(files) == 1
        assert "my_script.R" in files


class HgExcludedByDefaultTestCase(BaseRequiredFilesTestCase):
    source_contents = TOOL_REQUIRED_FILES_XML_3

    def test_expected_files(self):
        repo_dir = setup_dir_with_repo(self.temp_directory)
        files = self._required_files(repo_dir)
        assert len(files) == 1
        assert "my_script.R" in files


class HgExclusionDisabledTestCase(BaseRequiredFilesTestCase):
    source_contents = TOOL_REQUIRED_FILES_XML_DISABLED_DEFAULT_EXCLUSIONS

    def test_expected_files(self):
        repo_dir = setup_dir_with_repo(self.temp_directory)
        files = self._required_files(repo_dir)
        assert len(files) == 2
        assert "my_script.R" in files
        assert ".hg/index.R" in files


def setup_dir_with_repo(tmp_dir):
    repo = os.path.join(tmp_dir, "repo")
    os.makedirs(repo)
    hg = os.path.join(repo, ".hg")
    os.makedirs(hg)
    Path(hg, "index.R").touch()
    Path(repo, "my_script.R").touch()
    return repo

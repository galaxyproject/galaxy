import os
import shutil
import string
from contextlib import contextmanager

import pytest

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.tools.repositories import ValidationContext
from galaxy.util import galaxy_directory
from tool_shed.tools.tool_validator import ToolValidator

BISMARK_DIR = os.path.join(galaxy_directory(), "lib/tool_shed/test/test_data/repos/bismark/0")
BOWTIE2_INDICES = os.path.join(
    galaxy_directory(), "lib/tool_shed/test/test_data/bowtie2_loc_sample/bowtie2_indices.loc.sample"
)
MISSING_DATA_REF_DIR = os.path.join(galaxy_directory(), "lib/tool_shed/test/test_data/repos/missing_data_ref")
WRONG_DATA_REF_DIR = os.path.join(galaxy_directory(), "lib/tool_shed/test/test_data/repos/wrong_data_ref")


def test_validate_valid_tool():
    repo_dir = BISMARK_DIR
    with get_tool_validator() as tv:
        full_path = os.path.join(repo_dir, "bismark_methylation_extractor.xml")
        tool, valid, message = tv.load_tool_from_config(repository_id=None, full_path=full_path)
        assert tool.name == "Bismark"
        assert not tool.params_with_missing_data_table_entry
        assert not tool.params_with_missing_index_file
        assert valid is True
        assert message is None


def test_tool_validation_denies_allow_codefile():
    repo_dir = BISMARK_DIR
    with get_tool_validator() as tv:
        full_path = os.path.join(repo_dir, "bismark_methylation_extractor.xml")
        tool, valid, message = tv.load_tool_from_config(repository_id=None, full_path=full_path)
        assert tool._allow_code_files is False


def test_validate_tool_without_index():
    repo_dir = BISMARK_DIR
    with get_tool_validator() as tv:
        full_path = os.path.join(repo_dir, "bismark_bowtie2_wrapper.xml")
        tool, valid, message = tv.load_tool_from_config(repository_id=None, full_path=full_path)
        assert valid is True
        # tool is missing a data table
        assert tool.params_with_missing_data_table_entry
        # check input parameters, which will set up the missing data table (if present in repo_dir)
        invalid_files_and_errors_tups = tv.check_tool_input_params(
            repo_dir=os.path.dirname(full_path), tool_config_name=full_path, tool=tool, sample_files=[]
        )
        # tool is invalid because loc file is not present, but data table is present now
        assert len(invalid_files_and_errors_tups) == 1
        assert invalid_files_and_errors_tups[0][1].startswith("This file refers to a file named")
        assert not tool.params_with_missing_data_table_entry
        assert tool.params_with_missing_index_file
        # copy a loc file
        shutil.copy(BOWTIE2_INDICES, repo_dir)
        tool, valid, message, sample_files = tv.handle_sample_files_and_load_tool_from_disk(
            repo_dir, None, full_path, repo_dir
        )
        invalid_files_and_errors_tups = tv.check_tool_input_params(
            repo_dir=repo_dir, tool_config_name=full_path, tool=tool, sample_files=sample_files
        )
        # no parameters should be missing
        assert len(invalid_files_and_errors_tups) == 0
        assert not tool.params_with_missing_data_table_entry
        assert not tool.params_with_missing_index_file


def test_validate_missing_data_ref():
    repo_dir = MISSING_DATA_REF_DIR
    with get_tool_validator() as tv:
        full_path = os.path.join(repo_dir, "missing_data_ref.xml")
        tool, valid, message = tv.load_tool_from_config(repository_id=None, full_path=full_path)
        assert valid is False


def test_validate_wrong_data_ref():
    repo_dir = WRONG_DATA_REF_DIR
    with get_tool_validator() as tv:
        full_path = os.path.join(repo_dir, "wrong_data_ref.xml")
        tool, valid, message = tv.load_tool_from_config(repository_id=None, full_path=full_path)
        assert valid is False


DRILL_DOWN_FROM_FILE_TOOL = """<tool id="drill_down_from_file" name="drill_down_from_file" version="1.0.0">
    <command>echo '$parameter'</command>
    <inputs>
        <param name="parameter" type="drill_down" from_file="{from_file}" />
    </inputs>
    <outputs/>
</tool>
"""


def test_validation_does_not_read_drill_down_from_file(tmp_path):
    options_file = tmp_path / "options.xml"
    options_file.write_text('<options><option name="Option 1" value="option1"/></options>')
    with get_tool_validator() as tv:
        for from_file in [str(options_file), str(tmp_path / "missing.xml"), f"../../../../../../..{options_file}"]:
            full_path = tmp_path / "tool.xml"
            full_path.write_text(DRILL_DOWN_FROM_FILE_TOOL.format(from_file=from_file))
            tool, valid, message = tv.load_tool_from_config(repository_id=None, full_path=str(full_path))
            assert valid is True, message
            assert tool.inputs["parameter"].options == []


SELECT_FROM_FILE_TOOL = """<tool id="select_from_file" name="select_from_file" version="1.0.0">
    <command>echo '$parameter'</command>
    <inputs>
        <param name="parameter" type="select">
            <options from_file="{from_file}">
                <column name="value" index="0"/>
                <column name="name" index="0"/>
            </options>
        </param>
    </inputs>
    <outputs/>
</tool>
"""


def test_validation_keeps_select_from_file_in_work_dir(tmp_path):
    outside_file = tmp_path / "outside.loc"
    outside_file.write_text("secret\n")
    with get_tool_validator() as tv:
        work_dir = tv.app.config.tool_data_path
        with open(os.path.join(work_dir, "inside.loc"), "w") as fh:
            fh.write("value\n")
        os.symlink(outside_file, os.path.join(work_dir, "link.loc"))
        full_path = tmp_path / "tool.xml"

        def load_options(from_file):
            full_path.write_text(SELECT_FROM_FILE_TOOL.format(from_file=from_file))
            tool, valid, message = tv.load_tool_from_config(repository_id=None, full_path=str(full_path))
            assert valid is True, message
            return tool.inputs["parameter"].options

        options = load_options("inside.loc")
        assert options.index_file == "inside.loc"
        assert options.file_fields == [["value"]]
        for from_file in [os.path.relpath(outside_file, os.path.realpath(work_dir)), "link.loc"]:
            options = load_options(from_file)
            assert options.index_file is None
            assert options.missing_index_file == from_file
            assert options.file_fields is None


VALIDATOR_FILENAME_TOOL = """<tool id="validator_filename" name="validator_filename" version="1.0.0">
    <command>echo '$parameter'</command>
    <inputs>
        <param name="parameter" type="data" format="txt">
            <validator type="dataset_metadata_in_file" filename="{filename}" metadata_name="dbkey" metadata_column="0"/>
        </param>
    </inputs>
    <outputs/>
</tool>
"""

OUTPUT_ACTION_FROM_FILE_TOOL = """<tool id="output_action_from_file" name="output_action_from_file" version="1.0.0">
    <command>echo 'a' > '$output'</command>
    <inputs/>
    <outputs>
        <data name="output" format="txt">
            <actions>
                <action type="format">
                    <option type="from_file" name="{filename}" column="0"/>
                </action>
            </actions>
        </data>
    </outputs>
</tool>
"""


@pytest.mark.parametrize("tool_template", [VALIDATOR_FILENAME_TOOL, OUTPUT_ACTION_FROM_FILE_TOOL])
def test_validation_keeps_tool_data_files_in_work_dir(tmp_path, tool_template):
    outside_file = tmp_path / "outside.loc"
    outside_file.write_text("value\n")
    with get_tool_validator() as tv:
        work_dir = os.path.realpath(tv.app.config.tool_data_path)
        with open(os.path.join(work_dir, "inside.loc"), "w") as fh:
            fh.write("value\n")
        full_path = tmp_path / "tool.xml"

        def load(filename):
            full_path.write_text(tool_template.format(filename=filename))
            tool, valid, message = tv.load_tool_from_config(repository_id=None, full_path=str(full_path))
            return valid, message

        assert load("inside.loc") == (True, None)
        outside = os.path.relpath(outside_file, work_dir)
        missing = os.path.relpath(tmp_path / "missing.loc", work_dir)
        valid, message = load(outside)
        assert valid is False
        # an existing file outside the work dir is reported like a missing one
        assert load(missing) == (False, message.replace(outside, missing))


UNTRUSTED_PYTHON_TOOL = """<tool id="untrusted_python" name="untrusted_python" version="1.0.0">
    <command>echo '$expression' '$sanitized' '$from_parameter'</command>
    <inputs>
        <param name="expression" type="text">
            <validator type="expression">__import__('pathlib').Path('{marker}').touch() is None</validator>
        </param>
        <param name="sanitized" type="text">
            <sanitizer>
                <valid initial="string.digits if __import__('pathlib').Path('{marker}').touch() is None else ''"/>
            </sanitizer>
        </param>
        <param name="from_parameter" type="select">
            <options from_parameter="tool.app.config.tool_data_path" transform_lines="__import__('pathlib').Path('{marker}').touch() or []">
                <column name="value" index="0"/>
                <column name="name" index="0"/>
            </options>
        </param>
        <param name="digits" type="text">
            <sanitizer>
                <valid initial="string.digits"/>
            </sanitizer>
        </param>
    </inputs>
    <outputs/>
</tool>
"""


def test_validation_does_not_run_tool_python(tmp_path):
    marker = tmp_path / "marker"
    full_path = tmp_path / "tool.xml"
    full_path.write_text(UNTRUSTED_PYTHON_TOOL.format(marker=marker))
    with get_tool_validator() as tv:
        tool, valid, message = tv.load_tool_from_config(repository_id=None, full_path=str(full_path))
    assert valid is True, message
    assert not marker.exists()
    assert tool.inputs["expression"].optional is False
    assert tool.inputs["digits"].sanitizer.get_valid_by_name("string.digits") == list(string.digits)


TOOL_TEST_EXPRESSION_TOOL = """<tool id="tool_test_expression" name="tool_test_expression" version="1.0.0" profile="24.2">
    <command>echo '$expression' > '$output'</command>
    <inputs>
        <param name="expression" type="text" optional="true">
            <validator type="expression">__import__('pathlib').Path('{marker}').touch() is None</validator>
        </param>
    </inputs>
    <outputs>
        <data name="output" format="txt"/>
    </outputs>
    <tests>
        <test>
            <param name="expression" value="a"/>
            <output name="output" value="a.txt"/>
        </test>
    </tests>
</tool>
"""


def test_validation_does_not_run_tool_python_validating_tool_tests(tmp_path):
    marker = tmp_path / "marker"
    full_path = tmp_path / "tool.xml"
    full_path.write_text(TOOL_TEST_EXPRESSION_TOOL.format(marker=marker))
    with get_tool_validator() as tv:
        tool, valid, message = tv.load_tool_from_config(repository_id=None, full_path=str(full_path))
        assert valid is True, message
        tests = tool.tests
    assert not marker.exists()
    assert tests and not tests[0].exception


@contextmanager
def get_tool_validator():
    app = MockApp()
    with ValidationContext.from_app(app) as validation_context:
        yield ToolValidator(validation_context)

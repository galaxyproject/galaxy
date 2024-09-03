import os
import shutil
from contextlib import contextmanager

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.tools.repositories import ValidationContext
from galaxy.util import galaxy_directory
from tool_shed.tools.tool_validator import ToolValidator

BISMARK_DIR = os.path.join(galaxy_directory(), "lib/tool_shed/test/test_data/repos/bismark/0")
BOWTIE2_INDICES = os.path.join(
    galaxy_directory(), "lib/tool_shed/test/test_data/bowtie2_loc_sample/bowtie2_indices.loc.sample"
)


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


@contextmanager
def get_tool_validator():
    app = MockApp()
    with ValidationContext.from_app(app) as validation_context:
        yield ToolValidator(validation_context)

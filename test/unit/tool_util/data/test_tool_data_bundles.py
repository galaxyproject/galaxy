import csv
import json
import os
from dataclasses import dataclass

from galaxy.tool_util.data import (
    BUNDLE_INDEX_FILE_NAME,
    BundleProcessingOptions,
)
from galaxy.tool_util.data.bundles.models import (
    convert_data_tables_xml,
    DataTableBundleProcessorDescription,
)
from galaxy.util import (
    galaxy_directory,
    parse_xml,
)
from galaxy.util.resources import (
    as_file,
    resource_path,
)

TOOLS_DIRECTORY = os.path.abspath(os.path.join(galaxy_directory(), "test/functional/tools/"))


def test_xml_parsing() -> None:
    path = os.path.join(TOOLS_DIRECTORY, "sample_data_manager_conf.xml")
    tree = parse_xml(path)
    data_managers_el = tree.getroot()
    data_manager_el = data_managers_el.find("data_manager")
    assert data_manager_el is not None
    description = convert_data_tables_xml(data_manager_el)
    assert not description.undeclared_tables
    assert len(description.data_tables) == 1
    data_table = description.data_tables[0]
    output = data_table.output
    assert output
    columns = output.columns
    assert len(columns) == 2
    column1 = columns[0]
    assert column1.name == "value"
    assert column1.output_ref is None
    column2 = columns[1]
    assert column2.name == "path"
    assert column2.output_ref == "out_file"
    moves = column2.moves
    assert len(moves) == 1
    move = moves[0]
    assert move.type == "directory"
    assert move.relativize_symlinks is True
    assert move.target_base == "${GALAXY_DATA_MANAGER_DATA_PATH}"
    assert move.target_value == "testbeta/${value}"
    assert move.source_base is None
    assert move.source_value == ""


def test_parsing_manual() -> None:
    with as_file(resource_path(__name__, "example_data_managers/manual.xml")) as path:
        tree = parse_xml(path)
    data_managers_el = tree.getroot()
    data_manager_el = data_managers_el.find("data_manager")
    assert data_manager_el is not None
    description = convert_data_tables_xml(data_manager_el)
    assert description.undeclared_tables
    assert len(description.data_tables) == 0


def test_parsing_mothur() -> None:
    with as_file(resource_path(__name__, "example_data_managers/mothur.xml")) as path:
        tree = parse_xml(path)
    data_managers_el = tree.getroot()
    data_manager_el = data_managers_el.find("data_manager")
    assert data_manager_el is not None
    description = convert_data_tables_xml(data_manager_el)
    assert not description.undeclared_tables
    assert len(description.data_tables) == 4


@dataclass
class OutputDataset:
    file_name_: str
    extra_files_path: str
    ext: str = "data_manager_json"

    def get_file_name(self, sync_cache=True) -> str:
        return self.file_name_

    def extra_files_path_exists(self) -> bool:
        return os.path.exists(self.extra_files_path)


def prepare_typical_output_and_description(tmp_path):
    target_path = tmp_path / "newvalue.txt"
    target_path.write_text("Moo Cow")
    output = {"data_tables": {"testalpha": [{"value": "newvalue", "name": "mynewname", "path": "newvalue.txt"}]}}
    output_dataset_path = tmp_path / "output.dat"
    output_dataset_path.write_text(json.dumps(output))
    extra_files_path = tmp_path / "extra"
    extra_files_path.mkdir()
    output_dataset = OutputDataset(
        output_dataset_path,
        extra_files_path,
    )
    out_data = {"out1": output_dataset}
    data_table = {
        "name": "testalpha",
        "output": {
            "columns": [
                {
                    "name": "value",
                },
                {
                    "name": "name",
                },
                {
                    "name": "path",
                    "data_table_name": "path",
                    "output_ref": "out1",
                    "moves": [
                        {
                            "type": "directory",
                            "relativize_symlinks": True,
                            "target_value": "testalpha/${value}",
                            "target_base": "${GALAXY_DATA_MANAGER_DATA_PATH}",
                        }
                    ],
                    "value_translations": [
                        {"value": "${GALAXY_DATA_MANAGER_DATA_PATH}/testalpha/${value}/${path}", "type": "template"},
                        {"value": "abspath", "type": "function"},
                    ],
                },
            ]
        },
    }
    process_description = DataTableBundleProcessorDescription(
        **{
            "undeclared_tables": False,
            "data_tables": [data_table],
        }
    )
    return out_data, process_description


def test_typical_processing(tdt_manager, tmp_path):
    options = BundleProcessingOptions(
        what="data manager 'mock'",
        data_manager_path=str(tmp_path),
        target_config_file=str(tmp_path / "sample_data_managers_conf.xml"),
    )
    out_data, process_description = prepare_typical_output_and_description(tmp_path)
    repo_info = None
    tdt_manager.process_bundle(
        out_data,
        process_description,
        repo_info,
        options,
    )
    loc1 = tmp_path / "testalpha.loc"
    new_row = _last_row(loc1)
    assert new_row[0] == "newvalue"
    assert new_row[1] == "mynewname"
    assert new_row[2] == str(tmp_path / "testalpha" / "newvalue" / "newvalue.txt")


def test_write_bundle(tdt_manager, tmp_path):
    out_data, process_description = prepare_typical_output_and_description(tmp_path)
    tdt_manager.write_bundle(
        out_data,
        process_description,
        repo_info=None,
    )
    extra = tmp_path / "extra"
    bundle_index_json_path = extra / BUNDLE_INDEX_FILE_NAME
    assert bundle_index_json_path.exists()
    with open(bundle_index_json_path) as f:
        bundle_index = json.load(f)
    assert "processor_description" in bundle_index
    assert "data_tables" in bundle_index
    assert "output_name" in bundle_index


def test_import_bundle(tdt_manager, tmp_path):
    out_data, process_description = prepare_typical_output_and_description(tmp_path)
    tdt_manager.write_bundle(
        out_data,
        process_description,
        None,
    )

    # Writing the bundle didn't update the loc files.
    loc1 = tmp_path / "testalpha.loc"
    new_row = _last_row(loc1)
    assert new_row[0] != "newvalue"

    options = BundleProcessingOptions(
        what="data manager 'mock'",
        data_manager_path=str(tmp_path),
        target_config_file=str(tmp_path / "sample_data_managers_conf.xml"),
    )
    tdt_manager.import_bundle(
        str(tmp_path / "extra"),
        options,
    )

    # Importing the bundle does update the loc files though.
    loc1 = tmp_path / "testalpha.loc"
    new_row = _last_row(loc1)
    assert new_row[0] == "newvalue"
    assert new_row[1] == "mynewname"
    assert new_row[2] == str(tmp_path / "testalpha" / "newvalue" / "newvalue.txt")


def test_undeclared_tables(tdt_manager, tmp_path):
    options = BundleProcessingOptions(
        what="data manager 'mock'",
        data_manager_path=str(tmp_path),
        target_config_file=str(tmp_path / "sample_data_managers_conf.xml"),
    )
    target_path = tmp_path / "newvalue.txt"
    target_path.write_text("Moo Cow")
    output = {"data_tables": {"testalpha": [{"value": "newvalue", "name": "mynewname", "path": "newvalue.txt"}]}}
    output_dataset_path = tmp_path / "output.dat"

    output_dataset_path.write_text(json.dumps(output))
    extra_files_path = tmp_path / "extra"
    output_dataset = OutputDataset(
        output_dataset_path,
        extra_files_path,
    )
    out_data = {"out1": output_dataset}
    process_description = DataTableBundleProcessorDescription(
        **{
            "undeclared_tables": True,
            "data_tables": [],
        }
    )
    repo_info = None
    tdt_manager.process_bundle(
        out_data,
        process_description,
        repo_info,
        options,
    )
    loc1 = tmp_path / "testalpha.loc"
    new_row = _last_row(loc1)
    assert new_row[0] == "newvalue"
    assert new_row[1] == "mynewname"
    assert new_row[2] == str(tmp_path / "newvalue.txt")


def _last_row(loc_file):
    with open(loc_file) as file:
        rows = csv.reader(file, delimiter="\t")
        for row in rows:
            last_row = row
        return last_row

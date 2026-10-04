import subprocess
import sys
from xml.etree import ElementTree

import pyarrow.parquet as parquet
import pytest

from galaxy.datatypes.binary import Parquet
from galaxy.datatypes.registry import Registry
from galaxy.datatypes.tabular import (
    CSV,
    Tabular,
    TSV,
)
from ._parquet_converter_test_utils import (
    CONVERTERS,
    ROOT,
    to_parquet,
)


def test_converter_commands_and_datatype_registration(tmp_path):
    source = tmp_path / "input.tabular"
    binary = tmp_path / "output.parquet"
    tsv = tmp_path / "output.tsv"
    source.write_text("1\tapple\n2\tpear\n", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            str(CONVERTERS / "tabular_to_parquet_converter.py"),
            str(source),
            str(binary),
            "--input-format",
            "tabular",
            "--header-mode",
            "none",
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(CONVERTERS / "parquet_to_tabular_converter.py"),
            str(binary),
            str(tsv),
            "--output-format",
            "tsv",
        ],
        check=True,
    )
    assert to_parquet.read_table(tsv, input_format="tsv", header_mode="first").equals(parquet.read_table(binary))
    tool = ElementTree.parse(CONVERTERS / "parquet_to_tabular_converter.xml")
    assert tool.getroot().get("id") == "CONVERTER_parquet_to_tabular"
    assert tool.find("outputs/data").get("format") == "tabular"
    tsv_tool = ElementTree.parse(CONVERTERS / "parquet_to_tsv_converter.xml")
    assert tsv_tool.getroot().get("id") == "CONVERTER_parquet_to_tsv"
    assert tsv_tool.find("outputs/data").get("format") == "tsv"
    assert "--output-format tsv" in tsv_tool.find("command").text
    registry = ElementTree.parse(ROOT / "lib/galaxy/config/sample/datatypes_conf.xml.sample")
    assert (
        registry.find(".//datatype[@extension='parquet']/converter[@file='parquet_to_tabular_converter.xml']").get(
            "target_datatype"
        )
        == "tabular"
    )
    assert (
        registry.find(".//datatype[@extension='parquet']/converter[@file='parquet_to_tsv_converter.xml']").get(
            "target_datatype"
        )
        == "tsv"
    )
    assert registry.find(".//datatype[@extension='tsv']/converter[@file='tsv_to_parquet_converter.xml']") is not None


@pytest.mark.parametrize("accepted_format", ["tabular", "tsv", "csv"])
def test_parquet_is_offered_to_tools_accepting_each_output_format(accepted_format):
    config = ElementTree.parse(ROOT / "lib/galaxy/config/sample/datatypes_conf.xml.sample")
    registry = Registry()
    registry.datatypes_by_extension = {"parquet": Parquet(), "tabular": Tabular(), "tsv": TSV(), "csv": CSV()}
    registry.datatype_converters = {
        "parquet": {
            converter.get("target_datatype"): object()
            for converter in config.findall(".//datatype[@extension='parquet']/converter")
        }
    }
    assert registry.find_conversion_destination_for_dataset_by_extensions("parquet", [accepted_format]) == (
        False,
        accepted_format,
        None,
    )

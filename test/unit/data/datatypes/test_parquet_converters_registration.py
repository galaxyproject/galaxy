import subprocess
import sys
from typing import (
    cast,
    TYPE_CHECKING,
)
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import pytest

pytest.importorskip("pyarrow")

import pyarrow.parquet as parquet  # noqa: E402

from galaxy.datatypes.binary import Parquet  # noqa: E402
from galaxy.datatypes.registry import Registry  # noqa: E402
from galaxy.datatypes.tabular import (  # noqa: E402
    CSV,
    Tabular,
    TSV,
)
from .test_parquet_converter_utils import (  # noqa: E402
    CONVERTERS,
    ROOT,
    to_parquet,
)

if TYPE_CHECKING:
    from galaxy.tool_util.abstract_tool import AbstractTool


def _find_element(element: Element, path: str) -> Element:
    found = element.find(path)
    assert found is not None, f"Could not find {path}"
    return found


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
    assert _find_element(tool.getroot(), "outputs/data").get("format") == "tabular"
    tsv_tool = ElementTree.parse(CONVERTERS / "parquet_to_tsv_converter.xml")
    assert tsv_tool.getroot().get("id") == "CONVERTER_parquet_to_tsv"
    assert _find_element(tsv_tool.getroot(), "outputs/data").get("format") == "tsv"
    assert "--output-format tsv" in (_find_element(tsv_tool.getroot(), "command").text or "")
    registry = ElementTree.parse(ROOT / "lib/galaxy/config/sample/datatypes_conf.xml.sample")
    assert (
        _find_element(
            registry.getroot(),
            ".//datatype[@extension='parquet']/converter[@file='parquet_to_tabular_converter.xml']",
        ).get("target_datatype")
        == "tabular"
    )
    assert (
        _find_element(
            registry.getroot(),
            ".//datatype[@extension='parquet']/converter[@file='parquet_to_tsv_converter.xml']",
        ).get("target_datatype")
        == "tsv"
    )
    assert (
        _find_element(
            registry.getroot(),
            ".//datatype[@extension='tsv']/converter[@file='tsv_to_parquet_converter.xml']",
        )
        is not None
    )


@pytest.mark.parametrize("accepted_format", ["tabular", "tsv", "csv"])
def test_parquet_is_offered_to_tools_accepting_each_output_format(accepted_format):
    config = ElementTree.parse(ROOT / "lib/galaxy/config/sample/datatypes_conf.xml.sample")
    registry = Registry()
    registry.datatypes_by_extension = {"parquet": Parquet(), "tabular": Tabular(), "tsv": TSV(), "csv": CSV()}
    registry.datatype_converters = cast(
        "dict[str, dict[str, AbstractTool]]",
        {
            "parquet": {
                converter.get("target_datatype"): object()
                for converter in _find_element(config.getroot(), ".//datatype[@extension='parquet']").findall(
                    "converter"
                )
            }
        },
    )
    assert registry.find_conversion_destination_for_dataset_by_extensions("parquet", [accepted_format]) == (
        False,
        accepted_format,
        None,
    )

import pytest
from typing import Generator, Tuple
from typing_extensions import TypedDict

import galaxy.datatypes.interval

from .util import InputFileInfo, get_input_file_info, mock_urlopen

galaxy.datatypes.interval.urlopen = mock_urlopen
from galaxy.datatypes.interval import GTrack


@pytest.fixture
def gtrack_example_1() -> Generator[InputFileInfo, None, None]:
    return get_input_file_info("Example_1.gtrack", 0, read_contents=True)


@pytest.fixture
def gtrack_example_2() -> Generator[InputFileInfo, None, None]:
    return get_input_file_info("Example_2.gtrack", 1, read_contents=True)


@pytest.fixture
def gtrack_example_3() -> Generator[InputFileInfo, None, None]:
    return get_input_file_info("Example_3.gtrack", 2, read_contents=True)


@pytest.fixture
def gtrack_example_4() -> Generator[InputFileInfo, None, None]:
    return get_input_file_info("Example_4.gtrack", 3, read_contents=True)


@pytest.fixture
def gtrack_example_7B() -> Generator[InputFileInfo, None, None]:
    return get_input_file_info("Example_7B.gtrack", 3, read_contents=True)


@pytest.fixture
def gtrack_example_bed_direct() -> Generator[InputFileInfo, None, None]:
    return get_input_file_info("Example_bed_direct.gtrack", 3, read_contents=True)


@pytest.fixture
def gtrack_example_mean_sd_weights() -> Generator[InputFileInfo, None, None]:
    return get_input_file_info("Example_mean_sd_weights.gtrack", 4, read_contents=True)


@pytest.fixture
def gtrack_example_wig_segments() -> Generator[InputFileInfo, None, None]:
    return get_input_file_info("Example_wig_segments.gtrack", 5, read_contents=True)


@pytest.fixture
def gtrack_example_wig_step_function() -> Generator[InputFileInfo, None, None]:
    return get_input_file_info("Example_wig_step_function.gtrack", 6, read_contents=True)


@pytest.mark.parametrize(
    "input_file_fixture_name, expected",
    [
        ("gtrack_example_1", False),
        ("gtrack_example_2", True),
        ("gtrack_example_3", True),
        ("gtrack_example_4", True),
        ("gtrack_example_7B", True),
        ("gtrack_example_bed_direct", True),
        ("gtrack_example_mean_sd_weights", True),
        ("gtrack_example_wig_segments", True),
        ("gtrack_example_wig_step_function", True),
    ],
)
def test_gtrack_sniff_prefix(input_file_fixture_name, expected, request):
    input_file = request.getfixturevalue(input_file_fixture_name)
    with input_file as input_file_info:
        assert isinstance(input_file_info, InputFileInfo)
        assert GTrack().sniff_prefix(input_file_info.file_prefix) is expected


class GTrackMetadata(TypedDict):
    # Inherited from Interval
    chromCol: int
    startCol: int
    endCol: int
    strandCol: int
    nameCol: int
    viz_filter_cols: list
    columns: int

    # GTrack specific
    comment_lines: int
    data_lines: int
    header_lines: int
    bounding_regions: int
    column_names: Tuple[str, ...]
    column_types: Tuple[str, ...]
    delimiter: str


@pytest.mark.parametrize(
    "input_file_fixture_name, expected",
    [
        (
            "gtrack_example_1",
            GTrackMetadata(
                chromCol=1,
                startCol=2,
                endCol=3,
                columns=3,
                comment_lines=5,
                data_lines=2,
                header_lines=0,
                bounding_regions=0,
                column_names=("seqid", "start", "end"),
                column_types=("str", "int", "int"),
                delimiter="\t",
                track_type="segments",
            ),
        ),
        (
            "gtrack_example_2",
            GTrackMetadata(
                chromCol=1,
                startCol=2,
                endCol=3,
                nameCol=4,
                viz_filter_cols=[5],
                strandCol=6,
                columns=10,
                comment_lines=0,
                data_lines=6,
                header_lines=4,
                bounding_regions=0,
                column_names=(
                    "seqid",
                    "start",
                    "end",
                    "id",
                    "value",
                    "strand",
                    "thickStart",
                    "thickEnd",
                    "itemRgb",
                    "edges",
                ),
                column_types=("str", "int", "int", "str", "float", "str", "str", "str", "str", "str"),
                delimiter="\t",
                track_type="linked valued segments",
            ),
        ),
        (
            "gtrack_example_3",
            GTrackMetadata(
                endCol=1,
                nameCol=2,
                columns=4,
                comment_lines=2,
                data_lines=6,
                header_lines=4,
                bounding_regions=2,
                column_names=("end", "id", "directed", "edges"),
                column_types=("int", "str", "str", "str"),
                delimiter="\t",
                track_type="linked genome partition",
            ),
        ),
        (
            "gtrack_example_4",
            GTrackMetadata(
                chromCol=1,
                startCol=2,
                endCol=3,
                viz_filter_cols=[5],
                columns=5,
                comment_lines=3,
                data_lines=2,
                header_lines=3,
                bounding_regions=0,
                column_names=("seqid", "start", "end", "score1", "score2"),
                column_types=("str", "int", "int", "str", "float"),
                delimiter="\t",
                track_type="valued segments",
            ),
        ),
        (
            "gtrack_example_7B",
            GTrackMetadata(
                viz_filter_cols=[1],
                columns=1,
                comment_lines=5,
                data_lines=3,
                header_lines=1,
                bounding_regions=2,
                column_names=("value",),
                column_types=("str",),
                delimiter="\t",
                track_type="function",
            ),
        ),
        (
            "gtrack_example_bed_direct",
            GTrackMetadata(
                chromCol=1,
                startCol=2,
                endCol=3,
                nameCol=4,
                viz_filter_cols=[5],
                strandCol=6,
                columns=13,
                comment_lines=1,
                data_lines=2,
                header_lines=2,
                bounding_regions=0,
                column_names=(
                    "seqid",
                    "start",
                    "end",
                    "name",
                    "value",
                    "strand",
                    "thickStart",
                    "thickEnd",
                    "itemRgb",
                    "blockCount",
                    "blockSizes",
                    "blockStarts",
                    "description",
                ),
                column_types=(
                    "str",
                    "int",
                    "int",
                    "str",
                    "float",
                    "str",
                    "str",
                    "str",
                    "str",
                    "str",
                    "str",
                    "str",
                    "str",
                ),
                delimiter="\t",
                track_type="valued segments",
            ),
        ),
        (
            "gtrack_example_mean_sd_weights",
            GTrackMetadata(
                chromCol=1,
                startCol=2,
                endCol=3,
                nameCol=4,
                columns=5,
                comment_lines=0,
                data_lines=5,
                header_lines=2,
                bounding_regions=0,
                column_names=("seqid", "start", "end", "id", "edges"),
                column_types=("str", "int", "int", "str", "str"),
                delimiter="\t",
                track_type="linked segments",
            ),
        ),
        (
            "gtrack_example_wig_segments",
            GTrackMetadata(
                startCol=1,
                viz_filter_cols=[2],
                columns=2,
                comment_lines=3,
                data_lines=8,
                header_lines=3,
                bounding_regions=2,
                column_names=("start", "value"),
                column_types=("int", "float"),
                delimiter="\t",
                track_type="valued segments",
            ),
        ),
        (
            "gtrack_example_wig_step_function",
            GTrackMetadata(
                viz_filter_cols=[1],
                columns=1,
                comment_lines=3,
                data_lines=8,
                header_lines=4,
                bounding_regions=2,
                column_names=("value",),
                column_types=("float",),
                delimiter="\t",
                track_type="step function",
            ),
        ),
    ],
)
def test_gtrack_set_meta(input_file_fixture_name, expected, request):
    input_file = request.getfixturevalue(input_file_fixture_name)
    with input_file as input_file_info:
        assert isinstance(input_file_info, InputFileInfo)

        GTrack().set_meta(input_file_info.dataset)
        for key in expected.keys():
            assert getattr(input_file_info.dataset.metadata, key) == expected[key], (
                f"Unexpected value for {key}: input_file_info.metadata.{key} == "
                f"{getattr(input_file_info.dataset.metadata, key)}, expected: {expected[key]}"
            )

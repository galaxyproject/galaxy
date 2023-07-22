from typing import Generator, NamedTuple

import pytest

from galaxy.datatypes.interval import GTrack
from .util import InputFileInfo, get_input_file_info


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
def gtrack_example_bed_direct() -> Generator[InputFileInfo, None, None]:
    return get_input_file_info("Example_bed_direct.gtrack", 3, read_contents=True)


@pytest.fixture
def gtrack_example_mean_sd_weights() -> Generator[InputFileInfo, None, None]:
    return get_input_file_info("Example_mean_sd_weights.gtrack", 4, read_contents=True)


@pytest.mark.parametrize(
    "input_file_fixture_name, expected",
    [
        ("gtrack_example_1", False),
        ("gtrack_example_2", True),
        ("gtrack_example_3", True),
        ("gtrack_example_bed_direct", True),
        ("gtrack_example_mean_sd_weights", True),
    ],
)
def test_gtrack_sniff_prefix(input_file_fixture_name, expected, request):
    input_file = request.getfixturevalue(input_file_fixture_name)
    with input_file as input_file_info:
        assert isinstance(input_file_info, InputFileInfo)
        assert GTrack().sniff_prefix(input_file_info.file_prefix) is expected

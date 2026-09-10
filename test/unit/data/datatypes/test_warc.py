import pytest

from galaxy.datatypes.warc import (
    Warc,
    WarcGz,
)
from .util import get_input_files


@pytest.mark.parametrize(
    "loader, input_file",
    [
        [Warc, "example.warc"],
        [WarcGz, "example.warc.gz"],
    ],
)
def test_warc_sniff(loader, input_file):
    with get_input_files(input_file) as input_files:
        assert loader().sniff(input_files[0]) is True


@pytest.mark.parametrize(
    "loader, input_file",
    [
        [Warc, "Si.cif"],
        [WarcGz, "Si.cif"],
    ],
)
def test_warc_sniff_negative(loader, input_file):
    with get_input_files(input_file) as input_files:
        assert loader().sniff(input_files[0]) is False

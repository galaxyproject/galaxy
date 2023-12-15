import pytest

from galaxy.datatypes.text import (
    StormCheck,
    StormSample,
)
from .util import (
    get_input_files,
    MockDataset,
    MockDatasetDataset,
)


@pytest.mark.parametrize(
    "storm_loader, input_file",
    [
        [StormSample, "test_file2.storm.sample"],
        [StormCheck, "test_file2.storm.check"],
    ],
)
def test_storm_sniff(storm_loader, input_file):
    loader = storm_loader()
    with get_input_files(input_file) as input_files:
        assert loader.sniff(input_files[0]) is True


@pytest.mark.parametrize(
    "storm_loader, input_file, expected_peek",
    [
        [StormSample, "test_file2.storm.sample", """Storm-pars sample results."""],
        [StormCheck, "test_file2.storm.check", """Model checking result: true"""],
    ],
)
def test_storm_set_peek(storm_loader, input_file, expected_peek):
    loader = storm_loader()
    with get_input_files(input_file) as input_files:
        dataset = MockDataset(1)
        dataset.set_file_name(input_files[0])
        dataset.dataset = MockDatasetDataset(dataset.get_file_name())
        loader.set_peek(dataset)
        assert dataset.peek == expected_peek

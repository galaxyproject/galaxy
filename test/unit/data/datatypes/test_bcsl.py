import pytest

from galaxy.datatypes.text import (
    BCSLmodel,
    BCSLts,
    CTLresult,
)
from .util import (
    get_input_files,
    MockDataset,
    MockDatasetDataset,
)


@pytest.mark.parametrize(
    "bcsl_loader, input_file",
    [[BCSLmodel, "test_file3.bcsl.model"], [BCSLts, "test_file3.bcsl.ts"], [CTLresult, "test_file3.ctl.result"]],
)
def test_bcsl_sniff(bcsl_loader, input_file):
    loader = bcsl_loader()
    with get_input_files(input_file) as input_files:
        assert loader.sniff(input_files[0]) is True


@pytest.mark.parametrize(
    "bcsl_loader, input_file, expected_peek",
    [
        [BCSLts, "test_file3.bcsl.ts", "States: 12\nTransitions: 25\nUnique agents: 9\nInitial state: 2"],
        [CTLresult, "test_file3.ctl.result", """Model checking result: True"""],
    ],
)
def test_bcsl_set_peek(bcsl_loader, input_file, expected_peek):
    loader = bcsl_loader()
    with get_input_files(input_file) as input_files:
        dataset = MockDataset(1)
        dataset.set_file_name(input_files[0])
        dataset.dataset = MockDatasetDataset(dataset.get_file_name())
        loader.set_peek(dataset)
        assert dataset.peek == expected_peek

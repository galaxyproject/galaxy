import pytest

from galaxy.datatypes.text import (
    PithyaModel,
    PithyaProperty,
    PithyaResult,
)
from .util import get_input_files


@pytest.mark.parametrize(
    "pithya_loader, input_file",
    [
        [PithyaModel, "test_file1.pithya.model"],
        [PithyaProperty, "test_file1.pithya.property"],
        [PithyaResult, "test_file1.pithya.result"],
    ],
)
def test_pithya_sniff(pithya_loader, input_file):
    loader = pithya_loader()
    with get_input_files(input_file) as input_files:
        assert loader.sniff(input_files[0]) is True

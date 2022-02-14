import tempfile

from galaxy.datatypes.tabular import (
    MAX_DATA_LINES,
    Tabular,
)
from .util import MockDataset


def test_tabular_set_meta_large_file():
    with tempfile.NamedTemporaryFile(mode="w") as test_file:
        for _ in range(MAX_DATA_LINES + 1):
            test_file.write("A\tB\n")
        test_file.flush()
        dataset = MockDataset(id=1)
        dataset.file_name = test_file.name
        Tabular().set_meta(dataset)

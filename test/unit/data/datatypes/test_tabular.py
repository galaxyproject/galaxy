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
        dataset.set_file_name(test_file.name)
        Tabular().set_meta(dataset)  # type: ignore [arg-type]
        # data and comment lines are not stored if more than MAX_DATA_LINES
        assert dataset.metadata.data_lines is None
        assert dataset.metadata.comment_lines is None
        assert dataset.metadata.column_types == ["str", "str"]
        assert dataset.metadata.columns == 2
        assert dataset.metadata.delimiter == "\t"
        assert not hasattr(dataset.metadata, "column_names")

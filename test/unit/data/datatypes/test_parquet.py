from galaxy.datatypes.binary import Parquet
from galaxy.datatypes.sniff import get_test_fname
from .util import MockDataset


def test_parquet_set_meta_reads_footer_metadata():
    dataset = MockDataset(id=1)
    dataset.set_file_name(get_test_fname("example.parquet"))

    Parquet().set_meta(dataset)  # type: ignore[arg-type]

    assert dataset.metadata.column_names == ["one", "two", "three", "__index_level_0__"]
    assert dataset.metadata.column_count == 4
    assert dataset.metadata.line_count == 3

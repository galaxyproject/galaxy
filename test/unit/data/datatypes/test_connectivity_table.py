import os

import pytest

from galaxy.datatypes.tabular import ConnectivityTable
from galaxy.util import galaxy_directory


@pytest.fixture
def dataset():
    class MockDataset:
        def get_file_name(self, sync_cache=True):
            return os.path.join(galaxy_directory(), "test-data/1.ct")

    return MockDataset()


@pytest.fixture
def make_trans():
    class Stub:
        pass

    class StubTransaction:
        def __init__(self, chunk_size):
            self.app = Stub()
            self.app.config = Stub()  # type: ignore[attr-defined]
            self.app.config.display_chunk_size = chunk_size  # type: ignore[attr-defined]

    return StubTransaction


def test_get_chunk(dataset, make_trans):
    dt = ConnectivityTable()
    chunk_size = 1000
    trans = make_trans(chunk_size)
    chunk = dt.get_chunk(trans, dataset)
    assert (
        chunk
        == '{"ck_data": "363\\ttmRNA\\n1\\tG\\t0\\t2\\t359\\t1\\n2\\tG\\t1\\t3\\t358\\t2\\n", "offset": 38, "data_line_offset": 0}'
    )


def test_get_chunk_with_offset(dataset, make_trans):
    dt = ConnectivityTable()
    chunk_size = 10
    trans = make_trans(chunk_size)

    # reads chunk_size chars from offset 5 (line 1) to the end of line 2
    chunk = dt.get_chunk(trans, dataset, 5)
    assert chunk == '{"ck_data": "mRNA\\n1\\tG\\t0\\t2\\t359\\t1", "offset": 24, "data_line_offset": 0}'

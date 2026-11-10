import sqlite3

import pytest

from galaxy.datatypes.binary import SQlite
from galaxy.datatypes.dataproviders.dataset import (
    SQliteDataDictProvider,
    SQliteDataProvider,
    SQliteDataTableProvider,
)
from galaxy.exceptions import RequestParameterInvalidException
from ..util import MockDatasetDataset

PROVIDERS = [SQliteDataProvider, SQliteDataTableProvider, SQliteDataDictProvider]


class SQLiteSource:
    datatype = SQlite()

    def __init__(self, path):
        self.dataset = MockDatasetDataset(str(path))

    def __iter__(self):
        return iter(())


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "dataset_1.dat"
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE foo (id INTEGER PRIMARY KEY, col1 TEXT);
        INSERT INTO foo VALUES (1, 'a'), (2, 'b');
        """)
    connection.close()
    return SQLiteSource(path)


def test_table_provider_returns_rows(source):
    provider = SQliteDataTableProvider(source, query="SELECT col1 FROM foo ORDER BY id", headers=True)
    assert list(provider) == [["col1"], ["a"], ["b"]]


def test_dict_provider_returns_rows(source):
    provider = SQliteDataDictProvider(source, query="SELECT col1 FROM foo ORDER BY id")
    assert list(provider) == [[{"col1": "a"}], [{"col1": "b"}]]


@pytest.mark.parametrize("provider_class", PROVIDERS)
@pytest.mark.parametrize("query", ["DELETE FROM foo", "SELECT * FROM foo; DELETE FROM foo", "SELECT * FROM missing"])
def test_provider_rejects_query(source, provider_class, query):
    provider = provider_class(source, query=query)
    with pytest.raises(RequestParameterInvalidException):
        list(provider)
    connection = sqlite3.connect(source.dataset.get_file_name())
    assert connection.execute("SELECT count(*) FROM foo").fetchone()[0] == 2
    connection.close()


@pytest.mark.parametrize("provider_class", PROVIDERS)
def test_provider_interrupts_long_query(source, provider_class):
    short_timeout_provider_class = type("ShortTimeoutProvider", (provider_class,), {"query_timeout": 0.2})
    provider = short_timeout_provider_class(
        source, query="WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT x FROM c"
    )
    with pytest.raises(RequestParameterInvalidException, match="did not finish within 0.2 seconds"):
        list(provider)

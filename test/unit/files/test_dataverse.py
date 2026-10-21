import pytest

from galaxy.files.sources.dataverse import build_title_search_query


@pytest.mark.parametrize(
    "query, expected",
    [
        ("", "*"),
        ("handwritten medieval", "title:(+handwritten* +medieval*)"),
        ("handwritten-text", "title:(+handwritten* +text*)"),
        ("title:foo OR (bar", "title:(+title* +foo* +OR* +bar*)"),
    ],
)
def test_build_title_search_query(query, expected):
    assert build_title_search_query(query) == expected

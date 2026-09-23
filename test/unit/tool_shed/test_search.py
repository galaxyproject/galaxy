from functools import partial
from types import SimpleNamespace

import pytest
from whoosh import index

from galaxy.exceptions import ObjectNotFound
from tool_shed.webapp.search import (
    repo_search,
    tool_search,
)


@pytest.fixture(params=["tool", "repository"])
def search_index(request, tmp_path):
    kind = request.param
    config = SimpleNamespace(whoosh_index_dir=str(tmp_path))
    app = SimpleNamespace(config=config)
    if kind == "tool":
        index_dir = tmp_path / "tools"
        index_dir.mkdir()
        schema = tool_search.schema
        boosts = SimpleNamespace(
            tool_name_boost=1.2,
            tool_description_boost=0.6,
            tool_help_boost=0.4,
            tool_repo_owner_username_boost=0.3,
        )
        search = partial(tool_search.ToolSearch().search, app, "cutadapt", boosts=boosts)
    else:
        index_dir = tmp_path
        schema = repo_search.schema
        boosts = SimpleNamespace(
            repo_name_boost=1.2,
            repo_description_boost=0.6,
            repo_long_description_boost=0.4,
            repo_homepage_url_boost=0.3,
            repo_remote_repository_url_boost=0.3,
            repo_owner_username_boost=0.3,
            categories_boost=0.3,
        )
        trans = SimpleNamespace(app=app, security=SimpleNamespace(encode_id=str))
        search = partial(repo_search.RepoSearch().search, trans, "cutadapt", boosts=boosts)
    search_index = index.create_in(index_dir, schema)

    def populate(total):
        with search_index.writer() as writer:
            for i in range(total):
                document = dict(id=str(i) if kind == "tool" else i, name="cutadapt")
                if kind == "repository":
                    document.update(times_downloaded=1, approved="no")
                writer.add_document(**document)

    return kind, populate, search


@pytest.mark.parametrize("total,page_size", [(0, 2), (4, 2), (5, 2), (20, 20)])
def test_search_pagination(search_index, total, page_size):
    kind, populate, search = search_index
    populate(total)
    seen: set[str] = set()
    for page in (1, 2, 3, 4, 100):
        results = search(page=page, page_size=page_size)
        assert results["total_results"] == str(total)
        assert results["page"] == str(page)
        assert results["page_size"] == str(page_size)
        expected_count = min(page_size, max(0, total - (page - 1) * page_size))
        assert len(results["hits"]) == expected_count
        ids = {hit[kind]["id"] for hit in results["hits"]}
        assert len(ids) == expected_count
        assert not seen.intersection(ids)
        seen.update(ids)
    assert len(seen) == total


@pytest.mark.parametrize("page", [0, -1])
def test_search_invalid_page(search_index, page):
    _, populate, search = search_index
    populate(1)
    with pytest.raises(ObjectNotFound, match="The requested page does not exist"):
        search(page=page, page_size=2)

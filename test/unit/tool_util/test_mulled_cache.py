import json

from galaxy.tool_util.deps.mulled import mulled_cache


def test_quay_repositories_paginates():
    requests = []
    pages = [
        {"repositories": [{"name": "bwa"}], "next_page": "page-2"},
        {"repositories": [{"name": "samtools"}]},
    ]

    def fetch_json(endpoint, parameters):
        requests.append((endpoint, parameters))
        return pages.pop(0)

    repositories = mulled_cache.quay_repositories("biocontainers", fetch_json=fetch_json)

    assert repositories == ["bwa", "samtools"]
    assert requests[0][1] == {"public": "true", "namespace": "biocontainers"}
    assert requests[1][1]["next_page"] == "page-2"


def test_main_writes_cache_seed(monkeypatch, tmp_path):
    monkeypatch.setattr(mulled_cache, "quay_repositories", lambda namespace: ["bwa", "samtools"])
    output = tmp_path / "cache" / "seed.json"

    mulled_cache.main(["--namespace", "biocontainers", "--output", str(output)])

    assert json.loads(output.read_text()) == {
        "namespace": "biocontainers",
        "repositories": ["bwa", "samtools"],
    }

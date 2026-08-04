import json

from galaxy.tool_util.deps.mulled import mulled_cache


def test_main_writes_cache_seed(monkeypatch, tmp_path):
    monkeypatch.setattr(mulled_cache, "quay_repositories", lambda namespace: ["bwa", "samtools"])
    output = tmp_path / "cache" / "seed.json"

    mulled_cache.main(["--namespace", "biocontainers", "--output", str(output)])

    assert json.loads(output.read_text()) == {
        "namespace": "biocontainers",
        "repositories": ["bwa", "samtools"],
    }

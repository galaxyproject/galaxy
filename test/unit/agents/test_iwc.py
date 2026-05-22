from typing import (
    Any,
)
from unittest.mock import patch

import pytest

from galaxy.agents import iwc

SAMPLE_MANIFEST: list[dict[str, Any]] = [
    {
        "workflows": [
            {
                "trsID": "#workflow/github.com/iwc-workflows/sample-rnaseq/main",
                "definition": {
                    "name": "Sample RNA-seq",
                    "annotation": "An RNA-seq pipeline.",
                    "tags": ["rnaseq", "transcriptomics"],
                    "creator": [{"name": "Alice", "identifier": "0000-0001"}],
                    "steps": {
                        "0": {"tool_id": "toolshed.g2.bx.psu.edu/repos/iuc/fastqc/fastqc/0.73"},
                        "1": {"tool_id": "toolshed.g2.bx.psu.edu/repos/iuc/hisat2/hisat2/2.2.1"},
                    },
                },
                "readme": "# Title\n\nThis pipeline aligns reads with HISAT2.",
            }
        ]
    }
]


@pytest.fixture(autouse=True)
def _clear_cache():
    iwc.clear_manifest_cache()
    yield
    iwc.clear_manifest_cache()


def test_fetch_manifest_caches_response():
    with patch("galaxy.agents.iwc.requests.get") as mock_get:
        mock_get.return_value.json.return_value = SAMPLE_MANIFEST
        mock_get.return_value.raise_for_status.return_value = None

        first = iwc.fetch_manifest()
        second = iwc.fetch_manifest()

    assert first is second  # cache returns same object identity
    assert mock_get.call_count == 1


def test_clean_readme_summary_strips_headers_and_truncates():
    body = "First line that has plenty of content. Second line continues the thought. "
    readme = "# Heading\n\n" + (body * 10)
    out = iwc.clean_readme_summary(readme, max_length=80)
    assert "Heading" not in out
    assert out.endswith("...")
    assert len(out) <= 80


def test_extract_tool_names_dedupes_and_strips_repo_prefix():
    steps = SAMPLE_MANIFEST[0]["workflows"][0]["definition"]["steps"]
    names = iwc.extract_tool_names_from_steps(steps)
    assert names == ["fastqc", "hisat2"]


def test_enrich_workflow_includes_step_count_authors_tools():
    workflow = SAMPLE_MANIFEST[0]["workflows"][0]
    result = iwc.enrich_workflow(workflow)
    assert result["trsID"] == workflow["trsID"]
    assert result["step_count"] == 2
    assert result["authors"] == [{"name": "Alice", "orcid": "0000-0001"}]
    assert result["tools_used"] == ["fastqc", "hisat2"]
    assert result["readme_summary"]
    assert "readme" not in result  # excluded unless include_full_readme=True


def test_enrich_workflow_with_full_readme():
    workflow = SAMPLE_MANIFEST[0]["workflows"][0]
    result = iwc.enrich_workflow(workflow, include_full_readme=True)
    assert result["readme"] == workflow["readme"]


def test_search_workflows_ranks_token_overlap():
    workflows = SAMPLE_MANIFEST[0]["workflows"] + [
        {
            "trsID": "#workflow/github.com/iwc-workflows/proteomics/main",
            "definition": {"name": "Proteomics pipeline", "annotation": "MS analysis.", "tags": []},
            "readme": "Mass spec workflow.",
        }
    ]
    results = iwc.search_workflows(workflows, "rnaseq")
    assert results[0]["trsID"].endswith("sample-rnaseq/main")
    assert results[0]["match_score"] > 0


def test_search_workflows_respects_limit():
    workflows = [
        {
            "trsID": f"#workflow/github.com/iwc-workflows/wf-{i}/main",
            "definition": {"name": f"rnaseq pipeline {i}", "annotation": "", "tags": []},
            "readme": "",
        }
        for i in range(5)
    ]
    results = iwc.search_workflows(workflows, "rnaseq", limit=2)
    assert len(results) == 2


def test_search_workflows_empty_query_returns_nothing():
    results = iwc.search_workflows(SAMPLE_MANIFEST[0]["workflows"], "")
    assert results == []

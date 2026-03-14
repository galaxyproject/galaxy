from galaxy.util.pyodide import merge_execution_metadata


def test_merge_execution_metadata_prefers_pyodide_context_descriptors():
    metadata = {
        "pyodide_task": {
            "task_id": "t1",
            "code": "print('hi')",
            "original_code": "print('hi')",
            "packages": ["pandas"],
            "files": [{"id": "ds1", "url": "https://example", "name": "x.csv"}],
            "alias_map": {"ds1": "ds1"},
        },
        "pyodide_context": {
            "datasets": [{"id": "ds1", "name": "x.csv", "size": 123, "aliases": ["ds1", "x.csv"]}],
            "alias_map": {"ds1": "ds1"},
            "requirements": ["pandas"],
        },
    }
    merge_execution_metadata(
        metadata,
        task_id="t1",
        success=True,
        stdout="ok",
        stderr="",
        artifacts=[],
    )

    assert metadata["pyodide_status"] == "completed"
    assert metadata["stdout"] == "ok"
    assert "pyodide_task" not in metadata
    assert metadata["executed_task"]["code"] == "print('hi')"
    assert metadata["executed_task"]["requirements"] == ["pandas"]
    assert metadata["executed_task"]["datasets"] == metadata["pyodide_context"]["datasets"]
    assert metadata["executed_task"]["alias_map"] == metadata["pyodide_context"]["alias_map"]


def test_merge_execution_metadata_fallback_from_files_creates_descriptors_not_files():
    metadata = {
        "pyodide_task": {
            "task_id": "t2",
            "code": "print('hi')",
            "packages": ["pandas"],
            "files": [{"id": "ds2", "url": "https://example", "name": "y.tsv", "mime_type": "text/tab-separated-values"}],
        }
    }
    merge_execution_metadata(
        metadata,
        task_id="t2",
        success=False,
        stdout="",
        stderr="boom",
        artifacts=[],
    )

    datasets = metadata["executed_task"]["datasets"]
    assert isinstance(datasets, list) and datasets
    assert datasets[0]["id"] == "ds2"
    # Ensure we didn't leak download-only fields into dataset descriptors.
    assert "url" not in datasets[0]


def test_merge_execution_metadata_infers_plots_and_files_from_artifacts_when_missing():
    metadata = {
        "pyodide_task": {
            "task_id": "t3",
            "code": "print('hi')",
            "packages": ["pandas"],
            "files": [{"id": "ds3", "url": "https://example", "name": "z.csv"}],
        }
    }
    merge_execution_metadata(
        metadata,
        task_id="t3",
        success=True,
        stdout="ok",
        stderr="",
        artifacts=[
            {"name": "generated_file/plot.png", "mime_type": "image/png"},
            {"name": "table.csv", "mime_type": "text/csv"},
        ],
    )

    assert "generated_file/plot.png" in metadata.get("plots", [])
    assert "generated_file/table.csv" in metadata.get("files", [])

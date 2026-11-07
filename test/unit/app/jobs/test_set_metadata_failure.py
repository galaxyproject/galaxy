"""A failed standalone metadata operation must finalize its existing inputs."""

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from galaxy import (
    model,
    tools as tools_module,
)
from galaxy.model.unittest_utils import (
    GalaxyDataTestApp,
    GalaxyDataTestConfig,
)
from galaxy.tools import SetMetadataTool


class MetadataFailureTestConfig(GalaxyDataTestConfig):
    metadata_strategy = "directory"


@pytest.fixture(params=[False, True], ids=["history", "library"])
def failed_input(tmp_path, monkeypatch, request):
    app = GalaxyDataTestApp(MetadataFailureTestConfig(root=str(tmp_path / "app")))
    session = app.model.session
    history = model.History(name="Metadata failure")
    job = model.Job()
    job.tool_id, job.tool_version, job.history = "__SET_METADATA__", "1.0.3", history
    session.add_all([history, job])
    session.commit()
    cls = model.LibraryDatasetDatasetAssociation if request.param else model.HistoryDatasetAssociation
    dataset = cls(sa_session=session, create_dataset=True, extension="txt")
    session.add(dataset)
    if not request.param:
        history.add_dataset(dataset)
    assert dataset.dataset is not None
    app.object_store.create(dataset.dataset)
    Path(dataset.dataset.get_file_name()).write_bytes(b"existing input\n")
    dataset.dataset.state, dataset.dataset.file_size = model.Dataset.states.OK, Decimal(15)
    dataset.init_meta()
    dataset.metadata.data_lines = 7
    dataset.state = model.Dataset.states.SETTING_METADATA
    if request.param:
        job.add_input_library_dataset("input1", dataset)
    else:
        job.add_input_dataset("input1", dataset)
    session.commit()
    root = tmp_path / "job"
    directory = root / "metadata"
    directory.mkdir(parents=True)
    (directory / "metadata_results_input1").write_text(json.dumps([False, "not computed"]))
    (directory / "metadata_out_input1").write_text("{}")
    tool = object.__new__(SetMetadataTool)
    monkeypatch.setattr(tool, "app", app, raising=False)
    tool.id = "__SET_METADATA__"
    monkeypatch.setattr(tools_module, "JobWorkingDirectory", lambda *_: SimpleNamespace(resolve=lambda: str(root)))
    wrapper = SimpleNamespace(
        sa_session=session,
        job_id=job.id,
        app=app,
        get_param_dict=lambda: {},
    )
    try:
        yield SimpleNamespace(
            app=app, session=session, job=job, dataset=dataset, directory=directory, tool=tool, wrapper=wrapper
        )
    finally:
        session.remove()
        app.model.engine.dispose()


@pytest.mark.parametrize("failure", ["not_computed", "malformed_results", "import_exception"])
def test_failed_input_leaves_setting_metadata_even_if_results_cannot_be_imported(failed_input, failure):
    case = failed_input
    if failure == "malformed_results":
        (case.directory / "metadata_results_input1").write_text("{broken JSON")
    if failure == "import_exception":
        case.tool.exec_after_process = Mock(side_effect=RuntimeError("Import hook failed"))
        with pytest.raises(RuntimeError, match="Import hook failed"):
            case.tool.job_failed(case.wrapper, "Metadata failed")
    else:
        case.tool.job_failed(case.wrapper, "Metadata failed")
    case.session.refresh(case.dataset)
    assert case.dataset.state == model.Dataset.states.FAILED_METADATA
    assert Path(case.dataset.get_file_name()).read_bytes() == b"existing input\n"


def test_valid_results_are_preserved_after_a_later_job_failure(failed_input):
    case = failed_input
    (case.directory / "metadata_results_input1").write_text(json.dumps([True, "computed"]))
    (case.directory / "metadata_out_input1").write_text(json.dumps({"data_lines": 2, "comment_lines": 0}))
    case.tool.job_failed(case.wrapper, "Failure after metadata was computed")
    case.session.refresh(case.dataset)
    assert case.dataset.state == model.Dataset.states.OK
    assert case.dataset.metadata.data_lines == 2


def test_first_input_failure_also_finalizes_remaining_inputs(failed_input):
    case = failed_input
    another = type(case.dataset)(sa_session=case.session, create_dataset=True, extension="txt")
    case.session.add(another)
    another.dataset.state = model.Dataset.states.OK
    another.state = model.Dataset.states.SETTING_METADATA
    if isinstance(another, model.HistoryDatasetAssociation):
        case.job.history.add_dataset(another)
        case.job.add_input_dataset("input2", another)
    else:
        case.job.add_input_library_dataset("input2", another)
    case.session.commit()
    case.tool.job_failed(case.wrapper, "Metadata failed")
    for dataset in (case.dataset, another):
        case.session.refresh(dataset)
        assert dataset.state == model.Dataset.states.FAILED_METADATA


@pytest.mark.parametrize("protected", ["ok", "deleted", "purged", "dataset_deleted", "dataset_purged"])
def test_failure_does_not_replace_completed_metadata_or_revive_deleted_inputs(failed_input, protected):
    case = failed_input
    if protected == "ok":
        case.dataset.set_metadata_success_state()
    elif protected.startswith("dataset_"):
        setattr(case.dataset.dataset, protected.removeprefix("dataset_"), True)
    elif protected == "purged" and isinstance(case.dataset, model.LibraryDatasetDatasetAssociation):
        assert case.dataset.dataset is not None
        case.dataset.dataset.purged = True
    else:
        setattr(case.dataset, protected, True)
    case.session.commit()
    before = case.dataset.state, dict(case.dataset._metadata)
    case.tool.job_failed(case.wrapper, "Late metadata failure")
    case.session.refresh(case.dataset)
    assert (case.dataset.state, dict(case.dataset._metadata)) == before

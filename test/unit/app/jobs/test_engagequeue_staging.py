"""Local snapshots use Galaxy's normal evaluator path-rewrite hooks."""

import os
from pathlib import Path
from unittest.mock import (
    Mock,
    patch,
)

import pytest

from galaxy import model
from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.exceptions import ConfigurationError
from galaxy.job_execution.setup import JobIO
from galaxy.jobs.runners.engagequeue import _StagedInputComputeEnvironment
from galaxy.model.metadata import MetadataTempFile
from galaxy.tools.evaluation import ToolEvaluator


@pytest.fixture
def tools():
    owner = UsesTools()
    owner.setup_app()
    try:
        yield owner
    finally:
        owner.tear_down_app()


def dataset(root, identifier=1):
    root.mkdir(parents=True, exist_ok=True)
    primary = root / f"original-{identifier}.bam"
    primary.write_bytes(b"selected input\n")
    extra = root / f"extra-{identifier}"
    extra.mkdir()
    (extra / "inside").write_bytes(b"extra content\n")
    metadata = root / f"metadata-{identifier}.bai"
    metadata.write_bytes(b"metadata content\n")
    hda = model.HistoryDatasetAssociation(name="selected", extension="bam", metadata={})
    hda.dataset = model.Dataset(id=identifier, external_filename=str(primary))
    hda.dataset.external_extra_files_path = str(extra)
    hda.dataset.state = model.Dataset.states.OK
    hda.init_meta()
    index = MetadataTempFile()
    index._filename = str(metadata)
    hda.metadata.bam_index = index
    return hda


def environment(tmp_path: Path, job: model.Job) -> _StagedInputComputeEnvironment:
    directory = tmp_path / "job"
    directory.mkdir(exist_ok=True)
    job_io = Mock(
        spec=JobIO,
        working_directory=str(directory),
        file_sources_dict={},
        tool_directory=str(tmp_path),
        new_file_path=str(directory),
        version_path=str(directory / "version"),
        home_directory=str(directory / "home"),
        tmp_directory=str(directory / "tmp"),
        galaxy_url="http://galaxy.example",
        get_output_basenames=lambda: [],
        get_output_fnames=lambda: [],
    )
    return _StagedInputComputeEnvironment(job_io, job)


@pytest.mark.parametrize("kind", ["scalar", "collection", "materialized"])
def test_evaluator_rewrites_selected_primary_metadata_and_extra_paths(tools, tmp_path, kind, monkeypatch):
    app = tools.app
    selected = dataset(tmp_path / "permanent")
    original = selected.get_file_name()
    job = model.Job()
    job.history = model.History()
    job.history.id = 42
    job.add_input_dataset("input1", selected)
    incoming = {"input1": selected}
    input_xml = '<param name="input1" type="data" format="bam" />'
    expression = "$input1"
    materialized = {}
    if kind == "collection":
        collection = model.DatasetCollection(collection_type="list")
        collection.populated_state = "ok"
        collection.elements = [
            model.DatasetCollectionElement(element=selected, element_identifier="selected", element_index=0)
        ]
        hdca = model.HistoryDatasetCollectionAssociation(name="selected collection", collection=collection)
        incoming = {"input1": hdca}
        input_xml = '<param name="input1" type="data_collection" collection_type="list" format="bam" />'
        expression = "$input1[0]"
    elif kind == "materialized":
        replacement = dataset(tmp_path / "materialized", 2)
        materialized = {"input1": replacement}
        selected = replacement
    configs = (
        '<configfiles><configfile name="manifest">$input1.all_paths\n$input1.all_metadata_files</configfile></configfiles>'
        if kind == "collection"
        else ""
    )
    contents = f"""<tool id="stage_test" name="Stage test" version="1.0" profile="24.0">
    <command><![CDATA[read {expression} {expression}.metadata.bam_index {expression}.extra_files_path]]></command>
    <inputs>{input_xml}</inputs><outputs />{configs}</tool>"""
    tools._init_tool(tool_contents=contents)
    tool = tools.tool
    monkeypatch.setattr(tool, "params_from_strings", lambda *args, **kwargs: incoming)
    evaluator = ToolEvaluator(app, tool, job, str(tmp_path / "job"))
    monkeypatch.setattr(evaluator, "_validate_incoming", lambda *_: None)
    context = environment(tmp_path, job)
    with patch.object(evaluator, "_materialize_objects", return_value=materialized):
        evaluator.set_compute_environment(context)
    command, _, config_files, *_ = evaluator.build()
    assert original not in command
    primary = Path(context.input_path_rewrite(selected))
    extra = Path(context.input_extra_files_rewrite(selected))
    metadata_path = context.input_metadata_rewrite(selected, selected.metadata.bam_index.get_file_name())
    assert metadata_path is not None
    sidecar = Path(metadata_path)
    assert command == f"read {primary} {sidecar} {extra}"
    assert primary.read_bytes() == b"selected input\n"
    assert (extra / "inside").read_bytes() == b"extra content\n"
    assert sidecar.read_bytes() == b"metadata content\n"
    if kind == "collection":
        manifest = Path(config_files[0]).read_text()
        assert original not in manifest
        assert str(primary) in manifest and str(sidecar) in manifest
    assert all(path.is_relative_to(tmp_path / "job/inputs") for path in (primary, sidecar, extra))
    primary.write_bytes(b"job copy changed\n")
    assert Path(selected.get_file_name()).read_bytes() == b"selected input\n"
    assert not list((tmp_path / "job/inputs").rglob(".input-*"))


@pytest.mark.parametrize("absolute", [False, True])
def test_staged_extra_files_keep_internal_symlinks_within_snapshot(tmp_path, absolute):
    selected = dataset(tmp_path / "permanent")
    source = Path(selected.dataset.extra_files_path)
    (source / "link").symlink_to(source / "inside" if absolute else "inside")
    context = environment(tmp_path, model.Job())
    copied = Path(context.input_extra_files_rewrite(selected))
    assert (copied / "link").is_symlink()
    assert (copied / "link").resolve().is_relative_to(copied)
    assert (copied / "link").read_bytes() == b"extra content\n"
    assert os.readlink(source / "link") == str(source / "inside" if absolute else "inside")


def test_staged_extra_files_reject_escaping_symlink_without_partial_snapshot(tmp_path):
    selected = dataset(tmp_path / "permanent")
    source = Path(selected.dataset.extra_files_path)
    unrelated = tmp_path / "unrelated"
    unrelated.write_text("private")
    (source / "escape").symlink_to(unrelated)
    context = environment(tmp_path, model.Job())
    with pytest.raises(ConfigurationError, match="escapes"):
        context.input_extra_files_rewrite(selected)
    assert not context.staged_paths
    assert not list(context.directory.rglob(".input-*"))
    assert unrelated.read_text() == "private"


def test_interrupted_primary_copy_is_atomic_and_can_be_retried(tmp_path):
    selected = dataset(tmp_path / "permanent")
    context = environment(tmp_path, model.Job())
    with patch("galaxy.jobs.runners.engagequeue.shutil.copyfileobj", side_effect=OSError("copy interrupted")):
        with pytest.raises(OSError, match="interrupted"):
            context.input_path_rewrite(selected)
    assert not context.staged_paths
    assert not list(context.directory.rglob(".input-*"))
    copied = Path(context.input_path_rewrite(selected))
    assert copied.read_bytes() == b"selected input\n"

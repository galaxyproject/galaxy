import json
import os
import tempfile
from typing import (
    cast,
    TYPE_CHECKING,
)

import pytest

from galaxy import model
from galaxy.job_execution.output_collect import (
    collect_dynamic_outputs,
    dataset_collector,
)
from galaxy.model.dataset_collections import builder
from galaxy.model.store.discover import InvalidDiscoveredFilePathError
from galaxy.schema.schema import JobState
from galaxy.tool_util.parser.output_collection_def import (
    FilePatternDatasetCollectionDescription,
    ToolProvidedMetadataDatasetCollection,
)
from galaxy.tool_util.parser.output_objects import (
    ToolOutputCollection,
    ToolOutputCollectionStructure,
)
from galaxy.tool_util.provided_metadata import (
    BaseToolProvidedMetadata,
    NullToolProvidedMetadata,
    ToolProvidedMetadata,
)
from galaxy.tools import JobContext
from ..tools.test_history_imp_exp import _mock_app

if TYPE_CHECKING:
    from galaxy.tools import Tool


class PermissionProvider:
    def __init__(self):
        self.permissions = []

    def set_default_hda_permissions(self, primary_data):
        pass

    def copy_dataset_permissions(self, init_from, primary_data):
        pass


class MetadataSourceProvider:
    def get_metadata_source(self, input_name):
        return None


class MockTool:
    def __init__(self, app):
        self.app = app
        self.sa_session = app.model.context
        self.allows_unnamed_outputs = True
        self.allows_external_output_paths = False
        self.outputs = {}
        self.output_collections = {}


def setup_data(job_working_directory):
    for i in range(10):
        with open(os.path.join(job_working_directory, f"datasets_{i}.txt"), "w") as out:
            out.write(str(i))


def tool_provided_metadata(job_working_directory, dataset):
    metadata_path = os.path.join(job_working_directory, "galaxy.json")
    with open(metadata_path, "w") as metadata_file:
        json.dump({"output": {"datasets": [dataset]}}, metadata_file)
    return ToolProvidedMetadata(metadata_path)


def job_context_for_directory(job_working_directory, tool_provided_metadata: BaseToolProvidedMetadata | None = None):
    app = _mock_app()
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")
    h = model.History(name="Test History", user=u)

    tool = cast("Tool", MockTool(app))
    tool_provided_metadata = tool_provided_metadata or NullToolProvidedMetadata()
    job = model.Job()
    job.history = h
    sa_session.add(job)
    sa_session.commit()
    permission_provider = PermissionProvider()
    metadata_source_provider = MetadataSourceProvider()
    object_store = app.object_store
    input_dbkey = "?"
    final_job_state = JobState.OK
    collection = model.DatasetCollection(collection_type="list", populated=False)
    sa_session.add(collection)
    job_context = JobContext(
        tool,
        tool_provided_metadata,
        job,
        job_working_directory,
        permission_provider,
        metadata_source_provider,
        input_dbkey,
        object_store,
        final_job_state,
        max_discovered_files=100,
    )
    return app, sa_session, job_context, collection


def test_job_context_discover_outputs_flushes_once(mocker):
    job_working_directory = tempfile.mkdtemp()
    setup_data(job_working_directory)
    _app, sa_session, job_context, collection = job_context_for_directory(job_working_directory)
    collection_description = FilePatternDatasetCollectionDescription(pattern="__name__")
    collection_builder = builder.BoundCollectionBuilder(collection)
    dataset_collectors = [dataset_collector(collection_description)]
    output_name = "output"
    filenames = job_context.find_files(output_name, collection, dataset_collectors)
    assert len(filenames) == 10
    spy = mocker.spy(sa_session, "commit")
    job_context.populate_collection_elements(
        collection,
        collection_builder,
        filenames,
        name=output_name,
        metadata_source_name="",
        final_job_state=job_context.final_job_state,
    )
    collection_builder.populate()
    assert spy.call_count == 0
    sa_session.commit()
    assert len(collection.dataset_instances) == 10
    assert collection.dataset_instances[0].dataset.file_size == 1


def test_collection_rejects_tool_provided_extra_files_outside_working_directory():
    with tempfile.TemporaryDirectory() as job_working_directory:
        dataset_path = os.path.join(job_working_directory, "dataset.txt")
        with open(dataset_path, "w") as dataset_file:
            dataset_file.write("dataset")
        with tempfile.TemporaryDirectory() as outside_directory:
            metadata = tool_provided_metadata(
                job_working_directory,
                {
                    "filename": os.path.basename(dataset_path),
                    "name": "escaped extra files",
                    "extra_files": outside_directory,
                },
            )
            app, _sa_session, job_context, collection = job_context_for_directory(job_working_directory, metadata)
            collectors = [dataset_collector(ToolProvidedMetadataDatasetCollection())]
            discovered_files = job_context.find_files("output", collection, collectors)
            collection_builder = builder.BoundCollectionBuilder(collection)

            with pytest.raises(InvalidDiscoveredFilePathError):
                job_context.populate_collection_elements(
                    collection,
                    collection_builder,
                    discovered_files,
                    name="output",
                    metadata_source_name="",
                    final_job_state=job_context.final_job_state,
                )

            store_root = app.object_store.file_path
            assert not any(files for _dirpath, _dirnames, files in os.walk(store_root))


def test_collection_security_failure_marks_collection_failed_and_reraises():
    with tempfile.TemporaryDirectory() as job_working_directory:
        with tempfile.TemporaryDirectory() as outside_directory:
            outside_path = os.path.join(outside_directory, "sentinel.txt")
            with open(outside_path, "w") as outside_file:
                outside_file.write("sentinel")
            os.symlink(outside_path, os.path.join(job_working_directory, "escaped.txt"))
            _app, _sa_session, job_context, collection = job_context_for_directory(job_working_directory)
            collector_description = FilePatternDatasetCollectionDescription(pattern="__name__")
            collection_structure = ToolOutputCollectionStructure(
                collection_type="list",
                dataset_collector_descriptions=[collector_description],
            )
            job_context.tool.output_collections["output"] = ToolOutputCollection(
                "output",
                structure=collection_structure,
            )

            with pytest.raises(InvalidDiscoveredFilePathError):
                collect_dynamic_outputs(job_context, {"output": collection})

            assert collection.populated_state == collection.populated_states.FAILED
            assert collection.populated_state_message == "Problem building datasets for collection."

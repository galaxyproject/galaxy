import os
import tempfile

from galaxy import model
from galaxy.job_execution.output_collect import (
    dataset_collector,
    JobContext,
)
from galaxy.model.dataset_collections import builder
from galaxy.tool_util.parser.output_collection_def import FilePatternDatasetCollectionDescription
from galaxy.tool_util.provided_metadata import NullToolProvidedMetadata
from ..tools.test_history_imp_exp import _mock_app


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


class Tool:
    def __init__(self, app):
        self.app = app
        self.sa_session = app.model.context


def setup_data(job_working_directory):
    for i in range(10):
        with open(os.path.join(job_working_directory, f"datasets_{i}.txt"), "w") as out:
            out.write(str(i))


def test_job_context_discover_outputs_flushes_once(mocker):
    app = _mock_app()
    sa_session = app.model.context
    # mocker is a pytest-mock fixture

    u = model.User(email="collection@example.com", password="password")
    h = model.History(name="Test History", user=u)

    tool = Tool(app)
    tool_provided_metadata = NullToolProvidedMetadata()
    job = model.Job()
    job.history = h
    sa_session.add(job)
    sa_session.commit()
    job_working_directory = tempfile.mkdtemp()
    setup_data(job_working_directory)
    permission_provider = PermissionProvider()
    metadata_source_provider = MetadataSourceProvider()
    object_store = app.object_store
    input_dbkey = "?"
    final_job_state = "ok"
    collection_description = FilePatternDatasetCollectionDescription(pattern="__name__")
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

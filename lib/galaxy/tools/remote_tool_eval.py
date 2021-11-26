import json
import os
import shutil
import tempfile
import traceback
from typing import (
    Callable,
    NamedTuple,
)

from sqlalchemy.orm import scoped_session

from galaxy import model
from galaxy.datatypes.registry import Registry
from galaxy.files import ConfiguredFileSources
from galaxy.job_execution.compute_environment import SharedComputeEnvironment
from galaxy.job_execution.setup import JobIO
from galaxy.metadata.set_metadata import (
    get_metadata_params,
    get_object_store,
    validate_and_load_datatypes_config,
)
from galaxy.model import (
    Job,
    store,
)
from galaxy.objectstore import ObjectStore
from galaxy.tool_util.parser import get_tool_source
from galaxy.tools import (
    create_tool_from_source,
    evaluation,
)
from galaxy.tools.data import ToolDataTableManager
from galaxy.util.dbkeys import GenomeBuilds


class ToolAppConfig(NamedTuple):
    name: str
    tool_data_path: str
    nginx_upload_path: str
    len_file_path: str
    builds_file_path: str
    root: str
    is_admin_user: Callable
    admin_users: list = []


class ToolApp:
    """Dummy App that allows loading tools"""
    name = 'tool_app'
    model = model

    def __init__(
        self,
        sa_session: scoped_session,
        tool_app_config: ToolAppConfig,
        datatypes_registry: Registry,
        object_store: ObjectStore,
        tool_data_table_manager: ToolDataTableManager,
        file_sources: ConfiguredFileSources,
    ):
        self.model.context = sa_session  # type: ignore[attr-defined]
        self.config = tool_app_config
        self.datatypes_registry = datatypes_registry
        self.object_store = object_store
        self.genome_builds = GenomeBuilds(self)
        self.tool_data_tables = tool_data_table_manager
        self.file_sources = file_sources


def main(TMPDIR, WORKING_DIRECTORY):
    metadata_params = get_metadata_params(WORKING_DIRECTORY)
    datatypes_config = metadata_params["datatypes_config"]
    if not os.path.exists(datatypes_config):
        datatypes_config = os.path.join(WORKING_DIRECTORY, 'configs', datatypes_config)
    datatypes_registry = validate_and_load_datatypes_config(datatypes_config)
    object_store = get_object_store(WORKING_DIRECTORY)
    import_store = store.imported_store_for_metadata(os.path.join(WORKING_DIRECTORY, 'metadata', 'outputs_new'))
    job = next(iter(import_store.sa_session.objects[Job].values()))
    # TODO: clean up random places from which we read files in the working directory
    job_io = JobIO.from_json(os.path.join(WORKING_DIRECTORY, 'metadata', 'outputs_new', 'job_io.json'), sa_session=import_store.sa_session, job=job)
    tool_app_config = ToolAppConfig(
        name='tool_app',
        tool_data_path=job_io.tool_data_path,
        nginx_upload_path=TMPDIR,
        len_file_path=job_io.len_file_path,
        builds_file_path=job_io.builds_file_path,
        root=TMPDIR,
        is_admin_user=lambda _: job_io.user_context.is_admin)
    with open(os.path.join(WORKING_DIRECTORY, 'metadata', 'outputs_new', 'tool_data_tables.json')) as data_tables_json:
        tdtm = ToolDataTableManager.from_dict(json.load(data_tables_json))
    app = ToolApp(
        sa_session=import_store.sa_session,
        tool_app_config=tool_app_config,
        datatypes_registry=datatypes_registry,
        object_store=object_store,
        tool_data_table_manager=tdtm,
        file_sources=job_io.file_sources,
    )
    # TODO: could try to serialize just a minimal tool variant instead of the whole thing ?
    # FIXME: enable loading all supported tool types
    tool_source = get_tool_source(os.path.join(WORKING_DIRECTORY, 'metadata', 'outputs_new', 'tool.xml'))
    tool = create_tool_from_source(app, tool_source=tool_source)
    tool_evaluator = evaluation.ToolEvaluator(app=app, tool=tool, job=job, local_working_directory=WORKING_DIRECTORY)
    tool_evaluator.set_compute_environment(compute_environment=SharedComputeEnvironment(job_io=job_io, job=job))
    with open(os.path.join(WORKING_DIRECTORY, 'tool_script.sh'), 'w') as out:
        command_line, extra_filenames, environment_variables = tool_evaluator.build()
        out.write(command_line)


if __name__ == "__main__":
    TMPDIR = tempfile.mkdtemp()
    WORKING_DIRECTORY = os.getcwd()
    WORKING_PARENT = os.path.join(WORKING_DIRECTORY, os.path.pardir)
    if not os.path.isdir("working") and os.path.isdir(os.path.join(WORKING_PARENT, 'working')):
        # We're probably in pulsar
        WORKING_DIRECTORY = WORKING_PARENT
    try:
        main(TMPDIR, WORKING_DIRECTORY)
    except Exception:
        with open(os.path.join(WORKING_DIRECTORY, 'traceback.txt'), 'w') as out:
            out.write(traceback.format_exc())
        raise
    finally:
        shutil.rmtree(TMPDIR, ignore_errors=True)

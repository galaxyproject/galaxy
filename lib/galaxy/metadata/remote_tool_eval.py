import os
from typing import NamedTuple

from galaxy import model
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
from galaxy.tool_util.parser import get_tool_source
from galaxy.tools import (
    create_tool_from_source,
    evaluation,
)


class ToolAppConfig(NamedTuple):
    name: str
    tool_data_path: str
    root: str = '/tmp'
    admin_users: list = []


class ToolApp:
    """Dummy App that allows loading tools"""
    name = 'tool_app'
    model = model

    def __init__(self, sa_session, tool_app_config, datatypes_registry, object_store):
        self.model.context = sa_session
        self.config = tool_app_config
        self.datatypes_registry = datatypes_registry
        self.object_store = object_store


def main():
    WORKING_DIRECTORY = os.getcwd()
    metadata_params = get_metadata_params(WORKING_DIRECTORY)
    datatypes_config = metadata_params["datatypes_config"]
    datatypes_registry = validate_and_load_datatypes_config(datatypes_config)
    object_store = get_object_store()
    import_store = store.imported_store_for_metadata(WORKING_DIRECTORY)
    job = next(iter(import_store.sa_session.objects_by_class_and_id[Job].values()))
    tool_app_config = ToolAppConfig('tool_app', '/tmp')
    app = ToolApp(sa_session=import_store.sa_session, tool_app_config=tool_app_config, datatypes_registry=datatypes_registry, object_store=object_store)
    # TODO: could try to serialize just a minimal tool variant instead of the whole thing ?
    tool_source = get_tool_source(os.path.join(WORKING_DIRECTORY, 'tool.xml'))
    tool = create_tool_from_source(app, tool_source=tool_source)
    job_io = JobIO.from_json(os.path.join(WORKING_DIRECTORY, 'job_io.json'), sa_session=import_store.sa_session, job=job)

    tool_evaluator = evaluation.RemoteToolEvaluator(app=app, tool=tool, job=job, local_working_directory=WORKING_DIRECTORY, job_io=job_io)
    tool_evaluator.setup()
    with open(os.path.join(WORKING_DIRECTORY, 'tool_script.sh'), 'w') as out:
        command_line, extra_filenames, environment_variables = tool_evaluator.build()
        out.write(command_line)


if __name__ == "__main__":
    main()

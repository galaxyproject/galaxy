import os
from typing import NamedTuple

from galaxy import model
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
    for job in import_store.sa_session.objects:
        if isinstance(job, Job):
            break
    tool_app_config = ToolAppConfig('tool_app', '/tmp')
    app = ToolApp(sa_session=import_store.sa_session, tool_app_config=tool_app_config, datatypes_registry=datatypes_registry, object_store=object_store)
    tool_source = get_tool_source(os.path.join(WORKING_DIRECTORY, 'tool.xml'))
    tool = create_tool_from_source(app, tool_source=tool_source)

    tool_evaluator = evaluation.RemoteToolEvaluator(app=app, tool=tool, job=job, local_working_directory=WORKING_DIRECTORY)
    tool_evaluator.setup()
    tool_evaluator.build()


if __name__ == "__main__":
    main()

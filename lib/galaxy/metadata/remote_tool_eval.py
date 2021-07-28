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


WORKING_DIRECTORY = os.getcwd()
metadata_params = get_metadata_params(WORKING_DIRECTORY)
datatypes_config = metadata_params["datatypes_config"]

datatypes_registry = validate_and_load_datatypes_config(datatypes_config)
object_store = get_object_store()
import_store = store.imported_store_for_metadata(WORKING_DIRECTORY)
for job in import_store.sa_session.objects:
    if isinstance(job, Job):
        break


class ToolAppConfig(NamedTuple):
    name: str
    tool_data_path: str
    root: str = '/tmp'
    admin_users: list = []


class ToolApp:
    """Dummy App that allows loading tools"""
    config = ToolAppConfig('tool_app', '/tmp')
    name = 'tool_app'
    datatypes_registry = datatypes_registry
    model = model
    model.context = import_store.sa_session


app = ToolApp()
tool_source = get_tool_source(os.path.join(WORKING_DIRECTORY, 'tool.xml'))
tool = create_tool_from_source(app, tool_source=tool_source)

tool_evaluator = evaluation.RemoteToolEvaluator(app=app, tool=tool, job=job, local_working_directory=WORKING_DIRECTORY)
tool_evaluator.setup()
tool_evaluator.build()

import json
import os

from pydantic import TypeAdapter

from galaxy.tool_util_models import UserToolSource
from galaxy.tool_util_models.tool_outputs import IncomingUserToolOutput

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ToolSourceSchema.json")
schema = UserToolSource.model_json_schema()
authoring_output_schema = TypeAdapter(IncomingUserToolOutput).json_schema()
schema["$defs"].update(authoring_output_schema.get("$defs", {}))
with open(SCHEMA_PATH, "w") as fh:
    fh.write(json.dumps(schema))

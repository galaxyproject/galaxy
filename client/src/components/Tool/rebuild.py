import json
import os

from galaxy.tool_util_models import UserToolSource

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ToolSourceSchema.json")
with open(SCHEMA_PATH, "w") as fh:
    fh.write(json.dumps(UserToolSource.model_json_schema()))

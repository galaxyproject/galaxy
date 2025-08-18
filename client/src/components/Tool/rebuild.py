import json

from galaxy.tool_util_models import UserToolSource

with open("ToolSourceSchema.json", "w") as fh:
    fh.write(json.dumps(UserToolSource.model_json_schema()))

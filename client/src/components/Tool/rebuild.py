from galaxy.tool_util.models import UserToolSource

with open("ToolSourceSchema.json", "w") as fh:
    fh.write(UserToolSource.schema_json())

import json
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

import click
import yaml

from galaxy.webapps.galaxy.fast_app import get_openapi_schema


@click.command("Write openapi schema to path")
@click.argument("schema_path", type=click.Path(dir_okay=False, writable=True), required=False)
def write_open_api_schema(schema_path):
    openapi_schema = get_openapi_schema()
    if schema_path:
        if schema_path.endswith((".yml", ".yml")):
            with open(schema_path, "w") as f:
                yaml.safe_dump(openapi_schema, f)
        else:
            with open(schema_path, "w") as f:
                json.dump(openapi_schema, f, sort_keys=True)
    else:
        print(json.dumps(openapi_schema, sort_keys=True))


if __name__ == "__main__":
    write_open_api_schema()

import json
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

import click
import yaml
from pydantic.networks import (
    AnyUrl,
    url_regex,
)

from galaxy.webapps.galaxy.fast_app import get_openapi_schema


def _any_url_representer(dumper, data):
    return dumper.represent_scalar("!anyurl", str(data))


class YamlDumper(yaml.SafeDumper):
    pass


YamlDumper.add_representer(AnyUrl, _any_url_representer)
YamlDumper.add_implicit_resolver("!anyurl", url_regex(), None)


@click.command("Write openapi schema to path")
@click.argument("schema_path", type=click.Path(dir_okay=False, writable=True), required=False)
def write_open_api_schema(schema_path):
    openapi_schema = get_openapi_schema()
    if schema_path:
        if schema_path.endswith((".yml", ".yaml")):
            with open(schema_path, "w") as f:
                yaml.dump(openapi_schema, f, YamlDumper)
        else:
            with open(schema_path, "w") as f:
                json.dump(openapi_schema, f, sort_keys=True)
    else:
        print(json.dumps(openapi_schema, sort_keys=True))


if __name__ == "__main__":
    write_open_api_schema()

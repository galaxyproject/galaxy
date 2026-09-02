import json
from functools import lru_cache
from pathlib import Path
from typing import (
    Any,
    Optional,
)

import jsonschema
from referencing import (
    Registry,
    Resource,
)
from referencing.exceptions import NoSuchResource

from galaxy.util import requests
from galaxy_test.base import api_asserts

VENDORED_SCHEMAS_DIR = Path(__file__).parent / "schemas"

schema_store: dict[str, Any] = {}


@lru_cache(maxsize=1)
def vendored_schema_registry() -> Registry:
    """Build a registry mapping each vendored schema's ``$id`` URL to its local copy.

    Validation against these schemas resolves ``$ref``s entirely from the registry,
    so no network access is required.
    """
    resources = []
    for schema_path in sorted(VENDORED_SCHEMAS_DIR.glob("**/*.json")):
        with schema_path.open() as f:
            contents = json.load(f)
        resources.append((contents["$id"], Resource.from_contents(contents)))
    return Registry().with_resources(resources)


class JsonSchemaValidator:
    @staticmethod
    def validate_using_schema_url(instance: dict, schema_url: str):
        schema = schema_store.get(schema_url, None)
        if not schema:
            response = requests.get(schema_url)
            api_asserts.assert_status_code_is_ok(response)
            schema = response.json()
            schema_store[schema_url] = schema
        JsonSchemaValidator.validate(instance, schema)

    @staticmethod
    def validate_using_vendored_schema(instance: dict, schema_url: str):
        registry = vendored_schema_registry()
        try:
            schema = registry.contents(schema_url)
        except NoSuchResource:
            raise AssertionError(f"No vendored copy of schema {schema_url} found under {VENDORED_SCHEMAS_DIR}.")
        JsonSchemaValidator.validate(instance, schema, registry=registry)

    @staticmethod
    def validate(instance: dict, schema: dict, registry: Optional[Registry] = None):
        try:
            schema_version = schema.get("$id", "Unknown schema version")
            if registry is not None:
                jsonschema.validate(instance=instance, schema=schema, registry=registry)
            else:
                jsonschema.validate(instance=instance, schema=schema)
        except jsonschema.exceptions.ValidationError as err:
            raise AssertionError(
                f"The instance does not validate against the schema: {schema_version}.\nReasons:\n{err}"
            )

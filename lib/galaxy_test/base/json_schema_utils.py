from typing import (
    Any,
    Dict,
)

import jsonschema

from galaxy.util import requests
from galaxy_test.base import api_asserts

schema_store: Dict[str, Any] = {}


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
    def validate(instance: dict, schema: dict):
        try:
            schema_version = schema.get("$id", "Unknown schema version")
            jsonschema.validate(instance=instance, schema=schema)
        except jsonschema.exceptions.ValidationError as err:
            raise AssertionError(
                f"The instance does not validate against the schema: {schema_version}.\nReasons:\n{err}"
            )

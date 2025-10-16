"""
Copy of https://github.com/tiangolo/fastapi/blob/master/fastapi/openapi/utils.py with changes from https://github.com/tiangolo/fastapi/pull/10903
"""

from collections.abc import Sequence
from typing import (
    Any,
    Optional,
    Union,
)

from fastapi import routing
from fastapi._compat import (
    get_compat_model_name_map,
    get_definitions,
)
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.constants import REF_TEMPLATE
from fastapi.openapi.models import OpenAPI
from fastapi.openapi.utils import (
    get_fields_from_routes,
    get_openapi_path,
)
from pydantic.json_schema import GenerateJsonSchema
from starlette.routing import BaseRoute


def get_openapi(
    *,
    title: str,
    version: str,
    openapi_version: str = "3.1.0",
    summary: Optional[str] = None,
    description: Optional[str] = None,
    routes: Sequence[BaseRoute],
    webhooks: Optional[Sequence[BaseRoute]] = None,
    tags: Optional[list[dict[str, Any]]] = None,
    servers: Optional[list[dict[str, Union[str, Any]]]] = None,
    terms_of_service: Optional[str] = None,
    contact: Optional[dict[str, Union[str, Any]]] = None,
    license_info: Optional[dict[str, Union[str, Any]]] = None,
    separate_input_output_schemas: bool = True,
    schema_generator: Optional[GenerateJsonSchema] = None,
) -> dict[str, Any]:
    info: dict[str, Any] = {"title": title, "version": version}
    if summary:
        info["summary"] = summary
    if description:
        info["description"] = description
    if terms_of_service:
        info["termsOfService"] = terms_of_service
    if contact:
        info["contact"] = contact
    if license_info:
        info["license"] = license_info
    output: dict[str, Any] = {"openapi": openapi_version, "info": info}
    if servers:
        output["servers"] = servers
    components: dict[str, dict[str, Any]] = {}
    paths: dict[str, dict[str, Any]] = {}
    webhook_paths: dict[str, dict[str, Any]] = {}
    operation_ids: set[str] = set()
    all_fields = get_fields_from_routes(list(routes or []) + list(webhooks or []))
    model_name_map = get_compat_model_name_map(all_fields)
    schema_generator = schema_generator or GenerateJsonSchema(ref_template=REF_TEMPLATE)
    field_mapping, definitions = get_definitions(
        fields=all_fields,
        schema_generator=schema_generator,
        model_name_map=model_name_map,
        separate_input_output_schemas=separate_input_output_schemas,
    )
    for route in routes or []:
        if isinstance(route, routing.APIRoute):
            result = get_openapi_path(
                route=route,
                operation_ids=operation_ids,
                schema_generator=schema_generator,
                model_name_map=model_name_map,
                field_mapping=field_mapping,
                separate_input_output_schemas=separate_input_output_schemas,
            )
            if result:
                path, security_schemes, path_definitions = result
                if path:
                    paths.setdefault(route.path_format, {}).update(path)
                if security_schemes:
                    components.setdefault("securitySchemes", {}).update(security_schemes)
                if path_definitions:
                    definitions.update(path_definitions)
    for webhook in webhooks or []:
        if isinstance(webhook, routing.APIRoute):
            result = get_openapi_path(
                route=webhook,
                operation_ids=operation_ids,
                schema_generator=schema_generator,
                model_name_map=model_name_map,
                field_mapping=field_mapping,
                separate_input_output_schemas=separate_input_output_schemas,
            )
            if result:
                path, security_schemes, path_definitions = result
                if path:
                    webhook_paths.setdefault(webhook.path_format, {}).update(path)
                if security_schemes:
                    components.setdefault("securitySchemes", {}).update(security_schemes)
                if path_definitions:
                    definitions.update(path_definitions)
    if definitions:
        components["schemas"] = {k: definitions[k] for k in sorted(definitions)}
    if components:
        output["components"] = components
    output["paths"] = paths
    if webhook_paths:
        output["webhooks"] = webhook_paths
    if tags:
        output["tags"] = tags
    return jsonable_encoder(OpenAPI(**output), by_alias=True, exclude_none=True)

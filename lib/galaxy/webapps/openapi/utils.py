"""
Copy of fastapi/openapi/utils.py from https://github.com/fastapi/fastapi/pull/13918
"""

from collections.abc import Sequence
from typing import (
    Any,
)

from fastapi import routing
from fastapi._compat import (  # type: ignore[attr-defined,unused-ignore]
    get_flat_models_from_fields,
    get_model_name_map,
)
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.constants import REF_TEMPLATE
from fastapi.openapi.models import OpenAPI
from fastapi.openapi.utils import (
    _get_api_route_for_openapi,
    get_fields_from_routes,
    get_openapi_path,
)
from starlette.routing import BaseRoute

from ._compat import get_definitions
from ._compat.v2 import GenerateJsonSchema


def get_openapi(
    *,
    title: str,
    version: str,
    openapi_version: str = "3.1.0",
    summary: str | None = None,
    description: str | None = None,
    routes: Sequence[BaseRoute | routing.RouteContext],
    webhooks: Sequence[BaseRoute | routing.RouteContext] | None = None,
    tags: list[dict[str, Any]] | None = None,
    servers: list[dict[str, str | Any]] | None = None,
    terms_of_service: str | None = None,
    contact: dict[str, str | Any] | None = None,
    license_info: dict[str, str | Any] | None = None,
    separate_input_output_schemas: bool = True,
    external_docs: dict[str, Any] | None = None,
    schema_generator: GenerateJsonSchema | None = None,
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
    all_fields = get_fields_from_routes(list(routes) + list(webhooks or []))
    flat_models = get_flat_models_from_fields(all_fields, known_models=set())
    model_name_map = get_model_name_map(flat_models)
    schema_generator = schema_generator or GenerateJsonSchema(ref_template=REF_TEMPLATE)
    field_mapping, definitions = get_definitions(
        fields=all_fields,
        model_name_map=model_name_map,
        separate_input_output_schemas=separate_input_output_schemas,
        schema_generator=schema_generator,
    )
    for route_context in routing.iter_route_contexts(routes):
        api_route = _get_api_route_for_openapi(route_context)
        if api_route is not None:
            result = get_openapi_path(
                route=api_route,
                operation_ids=operation_ids,
                model_name_map=model_name_map,
                field_mapping=field_mapping,
                separate_input_output_schemas=separate_input_output_schemas,
            )
            if result:
                path, security_schemes, path_definitions = result
                if path:
                    paths.setdefault(api_route.path_format, {}).update(path)
                if security_schemes:
                    components.setdefault("securitySchemes", {}).update(security_schemes)
                if path_definitions:
                    definitions.update(path_definitions)
    for webhook_context in routing.iter_route_contexts(webhooks or []):
        api_webhook = _get_api_route_for_openapi(webhook_context)
        if api_webhook is not None:
            result = get_openapi_path(
                route=api_webhook,
                operation_ids=operation_ids,
                model_name_map=model_name_map,
                field_mapping=field_mapping,
                separate_input_output_schemas=separate_input_output_schemas,
            )
            if result:
                path, security_schemes, path_definitions = result
                if path:
                    webhook_paths.setdefault(api_webhook.path_format, {}).update(path)
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
    if external_docs:
        output["externalDocs"] = external_docs
    return jsonable_encoder(OpenAPI(**output), by_alias=True, exclude_none=True)

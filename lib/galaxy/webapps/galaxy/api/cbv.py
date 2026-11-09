"""
Original implementation by David Montague (@dmontagu)
https://github.com/dmontagu/fastapi-utils
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import (
    Any,
    ClassVar,
    get_origin,
    get_type_hints,
    TypeVar,
)

from fastapi import (
    APIRouter,
    Depends,
)
from fastapi.routing import APIRoute
from starlette.routing import (
    Route,
    WebSocketRoute,
)

T = TypeVar("T")

CBV_CLASS_KEY = "__cbv_class__"


def cbv(router: APIRouter) -> Callable[[type[T]], type[T]]:
    """
    This function returns a decorator that converts the decorated into a class-based view for the provided router.

    Any methods of the decorated class that are decorated as endpoints using the router provided to this function
    will become endpoints in the router. The first positional argument to the methods (typically `self`)
    will be populated with an instance created using FastAPI's dependency-injection.

    For more detail, review the documentation at
    https://fastapi-utils.davidmontague.xyz/user-guide/class-based-views/#the-cbv-decorator
    """

    def decorator(cls: type[T]) -> type[T]:
        return _cbv(router, cls)

    return decorator


def _cbv(router: APIRouter, cls: type[T]) -> type[T]:
    """
    Replaces any methods of the provided class `cls` that are endpoints of routes in `router` with updated
    function calls that will properly inject an instance of `cls`.
    """
    _init_cbv(cls)
    cbv_router = APIRouter()
    function_members = inspect.getmembers(cls, inspect.isfunction)
    functions_set = {func for _, func in function_members}
    cbv_routes = [
        route
        for route in router.routes
        if isinstance(route, (Route, WebSocketRoute)) and route.endpoint in functions_set
    ]
    for route in cbv_routes:
        router.routes.remove(route)
        _update_cbv_route_endpoint_signature(cls, route)
        cbv_router.routes.append(route)
    # Re-register HTTP routes to rebuild dependencies and handlers after changing
    # the endpoint signatures. Including a temporary router does this too,
    # but FastAPI >= 0.137 retains that extra level and walks it on every request.
    # Keep normal inclusion for WebSockets, inferred streams and custom constructors.
    if all(
        isinstance(route, APIRoute)
        and type(route).__init__ is APIRoute.__init__
        and not getattr(route, "stream_item_type", None)
        for route in cbv_routes
    ):
        for route in cbv_routes:
            assert isinstance(route, APIRoute)
            router.add_api_route(
                route.path,
                route.endpoint,
                response_model=route.response_model,
                status_code=route.status_code,
                tags=route.tags,
                dependencies=route.dependencies,
                summary=route.summary,
                description=route.description,
                response_description=route.response_description,
                responses=route.responses,
                deprecated=route.deprecated,
                methods=route.methods,
                operation_id=route.operation_id,
                response_model_include=route.response_model_include,
                response_model_exclude=route.response_model_exclude,
                response_model_by_alias=route.response_model_by_alias,
                response_model_exclude_unset=route.response_model_exclude_unset,
                response_model_exclude_defaults=route.response_model_exclude_defaults,
                response_model_exclude_none=route.response_model_exclude_none,
                include_in_schema=route.include_in_schema,
                response_class=route.response_class,
                name=route.name,
                route_class_override=type(route),
                callbacks=route.callbacks,
                openapi_extra=route.openapi_extra,
                generate_unique_id_function=route.generate_unique_id_function,
                strict_content_type=route.strict_content_type,
            )
    else:
        router.include_router(cbv_router)
    return cls


def _init_cbv(cls: type[Any]) -> None:
    """
    Idempotently modifies the provided `cls`, performing the following modifications:
    * The `__init__` function is updated to set any class-annotated dependencies as instance attributes
    * The `__signature__` attribute is updated to indicate to FastAPI what arguments should be passed to the initializer
    """
    if getattr(cls, CBV_CLASS_KEY, False):  # pragma: no cover
        return  # Already initialized
    old_init: Callable[..., Any] = cls.__init__
    old_signature = inspect.signature(old_init)
    old_parameters = list(old_signature.parameters.values())[1:]  # drop `self` parameter
    new_parameters = [
        x for x in old_parameters if x.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]
    dependency_names: list[str] = []
    for name, hint in get_type_hints(cls).items():
        if get_origin(hint) is ClassVar:
            continue
        parameter_kwargs = {"default": getattr(cls, name, Ellipsis)}
        dependency_names.append(name)
        new_parameters.append(
            inspect.Parameter(name=name, kind=inspect.Parameter.KEYWORD_ONLY, annotation=hint, **parameter_kwargs)
        )
    new_signature = old_signature.replace(parameters=new_parameters)

    def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
        for dep_name in dependency_names:
            dep_value = kwargs.pop(dep_name)
            setattr(self, dep_name, dep_value)
        old_init(self, *args, **kwargs)

    setattr(cls, "__signature__", new_signature)  # noqa: B010
    setattr(cls, "__init__", new_init)  # noqa: B010
    setattr(cls, CBV_CLASS_KEY, True)


def _update_cbv_route_endpoint_signature(cls: type[Any], route: Route | WebSocketRoute) -> None:
    """
    Fixes the endpoint signature for a cbv route to ensure FastAPI performs dependency injection properly.
    """
    old_endpoint = route.endpoint
    old_signature = inspect.signature(old_endpoint)
    old_parameters: list[inspect.Parameter] = list(old_signature.parameters.values())
    old_first_parameter = old_parameters[0]
    new_first_parameter = old_first_parameter.replace(default=Depends(cls))
    new_parameters = [new_first_parameter] + [
        parameter.replace(kind=inspect.Parameter.KEYWORD_ONLY) for parameter in old_parameters[1:]
    ]
    new_signature = old_signature.replace(parameters=new_parameters)
    setattr(route.endpoint, "__signature__", new_signature)  # noqa: B010

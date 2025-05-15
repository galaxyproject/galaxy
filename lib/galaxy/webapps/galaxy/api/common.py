"""This module contains utility functions shared across the api package."""

from typing import (
    Any,
    List,
    Optional,
    Set,
)

from fastapi import (
    Body,
    Path,
    Query,
    Request,
)
from typing_extensions import Annotated

from galaxy.schema import (
    FilterQueryParams,
    SerializationParams,
    ValueFilterQueryParams,
)
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    LibraryFolderDatabaseIdField,
)
from galaxy.schema.schema import (
    UpdateDatasetPermissionsPayload,
    UpdateDatasetPermissionsPayloadAliases,
)
from galaxy.util import listify

FolderIdPathParam = Annotated[
    LibraryFolderDatabaseIdField,
    Path(..., title="Folder ID", description="The encoded identifier of the library folder."),
]

HistoryIDPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="History ID", description="The encoded database identifier of the History."),
]

HistoryDatasetIDPathParam = Annotated[
    DecodedDatabaseIdField, Path(..., title="History Dataset ID", description="The ID of the History Dataset.")
]


HistoryItemIDPathParam = Annotated[
    DecodedDatabaseIdField, Path(..., title="History Item ID", description="The ID of the item (`HDA`/`HDCA`)")
]

HistoryHDCAIDPathParam = Annotated[
    DecodedDatabaseIdField, Path(..., title="History Dataset Collection ID", description="The ID of the `HDCA`.")
]


DatasetCollectionElementIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Dataset Collection Element ID", description="The encoded ID of the dataset collection element."),
]


UserIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="User ID", description="The ID of the user."),
]


GroupIDPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Group ID", description="The ID of the group."),
]


RoleIDPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Role ID", description="The ID of the role."),
]

UpdateDatasetPermissionsBody = Annotated[
    UpdateDatasetPermissionsPayloadAliases,
    Body(
        ...,
        examples=[
            UpdateDatasetPermissionsPayload(
                action="set_permissions",
                access_ids=[],
                manage_ids=[],
                modify_ids=[],
            ).model_dump()
        ],
    ),
]

LibraryIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Library ID", description="The ID of the Library."),
]

LibraryDatasetIdPathParam = Annotated[
    DecodedDatabaseIdField, Path(..., title="Library dataset ID", description="The encoded ID of the library dataset.")
]

NotificationIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Notification ID", description="The ID of the Notification."),
]


PageIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Page ID", description="The ID of the Page."),
]

QuotaIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Quota ID", description="The ID of the Quota."),
]

SerializationViewQueryParam = Annotated[
    Optional[str],
    Query(
        title="View",
        description="View to be passed to the serializer",
    ),
]

SerializationKeysQueryParam: Optional[str] = Query(
    None,
    title="Keys",
    description="Comma-separated list of keys to be passed to the serializer",
)

FilterQueryQueryParam: Optional[List[str]] = Query(
    default=None,
    title="Filter Query",
    description="Generally a property name to filter by followed by an (often optional) hyphen and operator string.",
    examples=["create_time-gt"],
)

FilterValueQueryParam: Optional[List[str]] = Query(
    default=None,
    title="Filter Value",
    description="The value to filter by.",
    examples=["2015-01-29"],
)

OffsetQueryParam: Optional[int] = Query(
    default=0,
    ge=0,
    title="Offset",
    description="Starts at the beginning skip the first ( offset - 1 ) items and begin returning at the Nth item",
)

LimitQueryParam: Optional[int] = Query(
    default=None,
    ge=1,
    title="Limit",
    description="The maximum number of items to return.",
)

OrderQueryParam: Optional[str] = Query(
    default=None,
    title="Order",
    description=(
        "String containing one of the valid ordering attributes followed (optionally) "
        "by '-asc' or '-dsc' for ascending and descending order respectively. "
        "Orders can be stacked as a comma-separated list of values."
    ),
)


def parse_serialization_params(
    view: Optional[str] = None,
    keys: Optional[str] = None,
    default_view: Optional[str] = None,
    **_,  # Additional params are ignored
) -> SerializationParams:
    key_list = None
    if keys:
        key_list = keys.split(",")
    return SerializationParams(view=view, keys=key_list, default_view=default_view)


def query_serialization_params(
    view: SerializationViewQueryParam = None,
    keys: Optional[str] = SerializationKeysQueryParam,
) -> SerializationParams:
    return parse_serialization_params(view=view, keys=keys)


def get_value_filter_query_params(
    q: Optional[List[str]] = FilterQueryQueryParam,
    qv: Optional[List[str]] = FilterValueQueryParam,
) -> ValueFilterQueryParams:
    """
    This function is meant to be used as a Dependency.
    See https://fastapi.tiangolo.com/tutorial/dependencies/#first-steps
    """
    return ValueFilterQueryParams(
        q=q,
        qv=qv,
    )


def get_filter_query_params(
    q: Optional[List[str]] = FilterQueryQueryParam,
    qv: Optional[List[str]] = FilterValueQueryParam,
    offset: Optional[int] = OffsetQueryParam,
    limit: Optional[int] = LimitQueryParam,
    order: Optional[str] = OrderQueryParam,
) -> FilterQueryParams:
    """
    This function is meant to be used as a Dependency.
    See https://fastapi.tiangolo.com/tutorial/dependencies/#first-steps
    """
    return FilterQueryParams(
        q=q,
        qv=qv,
        offset=offset,
        limit=limit,
        order=order,
    )


def normalize_permission_payload(
    payload_aliases: UpdateDatasetPermissionsPayloadAliases,
) -> UpdateDatasetPermissionsPayload:
    """Normalize the payload by choosing the first non-None value for each field.

    This is an attempt on supporting multiple aliases for the permissions params.
    There are several allowed names for the same role list parameter, i.e.: `access`, `access_ids`, `access_ids[]`
    """
    # TODO: Maybe we should choose only one way/naming and deprecate the others?
    payload = payload_aliases.model_dump()
    normalized_payload = {
        "action": payload.get("action"),
        "access_ids": payload.get("access_ids") or payload.get("access_ids[]") or payload.get("access"),
        "manage_ids": payload.get("manage_ids") or payload.get("manage_ids[]") or payload.get("manage"),
        "modify_ids": payload.get("modify_ids") or payload.get("modify_ids[]") or payload.get("modify"),
    }
    update_payload = UpdateDatasetPermissionsPayload.model_construct(**normalized_payload)
    return update_payload


def get_query_parameters_from_request_excluding(request: Request, exclude: Set[str]) -> dict:
    """Gets all the request query parameters excluding the given parameters names in `exclude` set.

    This is useful when an endpoint uses arbitrary or dynamic query parameters that
    cannot be anticipated or documented beforehand. The `exclude` set can be used to avoid
    including those parameters that are already handled by the endpoint.
    """
    extra_params = request.query_params._dict
    for param_name in exclude:
        extra_params.pop(param_name, None)
    return extra_params


def query_parameter_as_list(query):
    """Used as FastAPI dependable for query parameters that need to behave as a list of values separated by comma
    or as multiple instances of the same parameter.

    .. important:: the ``query`` annotation provided must define the ``alias`` exactly as the name of the actual parameter name.

    Usage example::

        ValueQueryParam = Query(
            default=None,
            alias="value", # Important! this is the parameter name that will be displayed in the API docs
            title="My Value",
            description="A single value, a comma-separated list of values or a list of values.",
        )

        @router.get("/api/my_route")
        def index(
            self,
            values: Optional[List[str]] = Depends(query_parameter_as_list(ValueQueryParam)),
        ):
            ...

    This will render in the API docs as a single string query parameter but will make the following requests equivalent:

    - ``api/my_route?value=val1,val2,val3``
    - ``api/my_route?value=val1&value=val2&value=val3``
    """

    def parse_elements(
        elements: Optional[List[str]] = query,
    ) -> Optional[List[Any]]:
        if query.default != Ellipsis and not elements:
            return query.default
        if elements and len(elements) == 1:
            return listify(elements[0])
        return elements

    return parse_elements

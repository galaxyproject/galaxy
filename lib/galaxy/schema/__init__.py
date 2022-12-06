from datetime import datetime
from enum import Enum
from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
    Required,
)


class BootstrapAdminUser(BaseModel):
    id = 0
    email: Optional[str] = None
    preferences: Dict[str, str] = {}
    bootstrap_admin_user = True

    def all_roles(*args) -> list:
        return []


class ValueFilterQueryParams(BaseModel):
    """Allows filtering/querying elements by value like `q=<property>-<operator>&qv=<value>`

    Multiple `q/qv` queries can be concatenated.
    """

    q: Optional[Union[List[str], str]] = Field(
        default=None,
        title="Filter Query",
        description="Generally a property name to filter by followed by an (often optional) hyphen and operator string.",
        example="create_time-gt",
    )
    qv: Optional[Union[List[str], str]] = Field(
        default=None,
        title="Filter Value",
        description="The value to filter by.",
        example="2015-01-29",
    )


class PaginationQueryParams(BaseModel):
    """Used to paginate a the request results by limiting and offsetting."""

    offset: Optional[int] = Field(
        default=0,
        ge=0,
        title="Offset",
        description="Starts at the beginning skip the first ( offset - 1 ) items and begin returning at the Nth item",
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        title="Limit",
        description="The maximum number of items to return.",
    )


class FilterQueryParams(ValueFilterQueryParams, PaginationQueryParams):
    """Contains full filtering options to query elements, paginate and order them."""

    order: Optional[str] = Field(
        default=None,
        title="Order",
        description=(
            "String containing one of the valid ordering attributes followed (optionally) "
            "by '-asc' or '-dsc' for ascending and descending order respectively. "
            "Orders can be stacked as a comma-separated list of values."
        ),
        example="name-dsc,create_time",
    )


class SerializationParams(BaseModel):
    """Contains common parameters for customizing model serialization."""

    view: Optional[str] = Field(
        default=None,
        title="View",
        description=(
            "The name of the view used to serialize this item. "
            "This will return a predefined set of attributes of the item."
        ),
        example="summary",
    )
    keys: Optional[List[str]] = Field(
        default=None,
        title="Keys",
        description=(
            "List of keys (name of the attributes) that will be returned in addition "
            "to the ones included in the `view`."
        ),
    )
    default_view: Optional[str] = Field(
        default=None,
        title="Default View",
        description="The item view that will be used in case none was specified.",
    )


class PdfDocumentType(str, Enum):
    invocation_report = "invocation_report"
    page = "page"


class APIKeyModel(BaseModel):
    key: str = Field(Required, title="Key", description="API key to interact with the Galaxy API")
    create_time: datetime = Field(
        Required, title="Create Time", description="The time and date this API key was created."
    )

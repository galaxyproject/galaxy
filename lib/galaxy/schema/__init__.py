from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
)


class BootstrapAdminUser(BaseModel):
    id = 0
    email: Optional[str] = None
    preferences: Dict[str, str] = {}
    bootstrap_admin_user = True

    def all_roles(*args) -> list:
        return []


class FilterQueryParams(BaseModel):
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

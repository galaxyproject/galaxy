from enum import Enum
from typing import (
    List,
    Optional,
)

from pydantic import (
    Field,
    RootModel,
)
from typing_extensions import Literal

from galaxy.schema.fields import (
    EncodedDatabaseIdField,
    ModelClassField,
)
from galaxy.schema.schema import (
    GroupModel,
    Model,
    UserModel,
    WithModelClass,
)

QUOTA = Literal["Quota"]
USER_QUOTA_ASSOCIATION = Literal["UserQuotaAssociation"]
GROUP_QUOTA_ASSOCIATION = Literal["GroupQuotaAssociation"]
DEFAULT_QUOTA_ASSOCIATION = Literal["DefaultQuotaAssociation"]


class QuotaOperation(str, Enum):
    EXACT = "="
    ADD = "+"
    SUBTRACT = "-"


class DefaultQuotaTypes(
    str, Enum
):  # TODO: should this replace lib.galaxy.model.DefaultQuotaAssociation.types at some point?
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"


class DefaultQuotaValues(str, Enum):
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    NO = "no"


QuotaNameField = Field(
    ...,
    title="Name",
    description="The name of the quota. This must be unique within a Galaxy instance.",
)

QuotaDescriptionField = Field(
    ...,
    title="Description",
    description="Detailed text description for this Quota.",
)

QuotaOperationField = Field(
    QuotaOperation.EXACT,
    title="Operation",
    description=(
        "Quotas can have one of three `operations`:"
        "- `=` : The quota is exactly the amount specified"
        "- `+` : The amount specified will be added to the amounts of the user's other associated quota definitions"
        "- `-` : The amount specified will be subtracted from the amounts of the user's other associated quota definitions"
    ),
)


class DefaultQuota(
    Model, WithModelClass
):  # TODO: should this replace lib.galaxy.model.DefaultQuotaAssociation at some point?
    model_class: DEFAULT_QUOTA_ASSOCIATION = ModelClassField(DEFAULT_QUOTA_ASSOCIATION)
    type: DefaultQuotaTypes = Field(
        ...,
        title="Type",
        description=(
            "The type of the default quota. Either one of:\n"
            " - `registered`: the associated quota will affect registered users.\n"
            " - `unregistered`: the associated quota will affect unregistered users.\n"
        ),
    )


class UserQuota(Model, WithModelClass):
    model_class: USER_QUOTA_ASSOCIATION = ModelClassField(USER_QUOTA_ASSOCIATION)
    user: UserModel = Field(
        ...,
        title="User",
        description="Information about a user associated with a quota.",
    )


class GroupQuota(Model, WithModelClass):
    model_class: GROUP_QUOTA_ASSOCIATION = ModelClassField(GROUP_QUOTA_ASSOCIATION)
    group: GroupModel = Field(
        ...,
        title="Group",
        description="Information about a user group associated with a quota.",
    )


class QuotaBase(Model, WithModelClass):
    """Base model containing common fields for Quotas."""

    model_class: QUOTA = ModelClassField(QUOTA)
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="The `encoded identifier` of the quota.",
    )
    name: str = QuotaNameField
    quota_source_label: Optional[str] = Field(
        None,
        title="Quota Source Label",
        description="Quota source label",
    )


class QuotaSummary(QuotaBase):
    """Contains basic information about a Quota"""

    url: str = Field(
        ...,
        title="URL",
        description="The relative URL to get this particular Quota details from the rest API.",
        # TODO: also deprecate on python side, https://github.com/pydantic/pydantic/issues/2255
        json_schema_extra={"deprecated": True},
    )


class QuotaSummaryList(RootModel):
    root: List[QuotaSummary] = Field(
        default=[],
        title="List with summary information of Quotas.",
    )


class QuotaDetails(QuotaBase):
    description: str = QuotaDescriptionField
    bytes: int = Field(
        ...,
        title="Bytes",
        description="The amount, expressed in bytes, of this Quota.",
    )
    operation: QuotaOperation = QuotaOperationField
    display_amount: str = Field(
        ...,
        title="Display Amount",
        description="Human-readable representation of the `amount` field.",
    )
    default: List[DefaultQuota] = Field(
        [],
        title="Default",
        description="A list indicating which types of default user quotas, if any, are associated with this quota.",
    )
    users: List[UserQuota] = Field(
        [],
        title="Users",
        description="A list of specific users associated with this quota.",
    )
    groups: List[GroupQuota] = Field(
        [],
        title="Groups",
        description="A list of specific groups of users associated with this quota.",
    )


class CreateQuotaResult(QuotaSummary):
    message: str = Field(
        ...,
        title="Message",
        description="Text message describing the result of the operation.",
    )


class CreateQuotaParams(Model):
    name: str = QuotaNameField
    description: str = QuotaDescriptionField
    amount: str = Field(
        ...,
        title="Amount",
        description="Quota size (E.g. ``10000MB``, ``99 gb``, ``0.2T``, ``unlimited``)",
    )
    operation: QuotaOperation = QuotaOperationField
    default: DefaultQuotaValues = Field(
        default=DefaultQuotaValues.NO,
        title="Default",
        description=(
            "Whether or not this is a default quota. Valid values"
            " are ``no``, ``unregistered``, ``registered``. None is"
            " equivalent to ``no``."
        ),
    )
    quota_source_label: Optional[str] = Field(
        default=None,
        title="Quota Source Label",
        description="If set, quota source label to apply this quota operation to. Otherwise, the default quota is used.",
    )
    in_users: Optional[List[str]] = Field(
        default=[],
        title="Users",
        description="A list of user IDs or user emails to associate with this quota.",
    )
    in_groups: Optional[List[str]] = Field(
        default=[],
        title="Groups",
        description="A list of group IDs or names to associate with this quota.",
    )


class UpdateQuotaParams(Model):
    name: Optional[str] = Field(
        default=None,
        title="Name",
        description="The new name of the quota. This must be unique within a Galaxy instance.",
    )
    description: Optional[str] = Field(
        None,
        title="Description",
        description="Detailed text description for this Quota.",
    )
    amount: Optional[str] = Field(
        None,
        title="Amount",
        description="Quota size (E.g. ``10000MB``, ``99 gb``, ``0.2T``, ``unlimited``)",
    )
    operation: QuotaOperation = Field(
        QuotaOperation.EXACT,
        title="Operation",
        description=(
            "One of (``+``, ``-``, ``=``). If you wish to change this value,"
            " you must also provide the ``amount``, otherwise it will not take effect."
        ),
    )
    default: Optional[DefaultQuotaValues] = Field(
        default=None,
        title="Default",
        description=(
            "Whether or not this is a default quota. Valid values"
            " are ``no``, ``unregistered``, ``registered``."
            ' Calling this method with ``default="no"`` on a'
            " non-default quota will throw an error. Not"
            " passing this parameter is equivalent to passing ``no``."
        ),
    )
    in_users: Optional[List[str]] = Field(
        default=None,
        title="Users",
        description="A list of user IDs or user emails to associate with this quota.",
    )
    in_groups: Optional[List[str]] = Field(
        default=None,
        title="Groups",
        description="A list of group IDs or names to associate with this quota.",
    )


class DeleteQuotaPayload(Model):
    purge: bool = Field(
        False,
        title="Purge",
        description="Whether to also purge the Quota after deleting it.",
    )

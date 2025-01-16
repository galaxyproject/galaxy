"""
Galaxy data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""

import abc
import base64
import errno
import json
import logging
import numbers
import operator
import os
import pwd
import random
import string
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
)
from decimal import Decimal
from enum import Enum
from secrets import token_hex
from string import Template
from typing import (
    Any,
    cast,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    List,
    NamedTuple,
    Optional,
    overload,
    Set,
    Tuple,
    Type,
    TYPE_CHECKING,
    TypeVar,
    Union,
)
from uuid import (
    UUID,
    uuid4,
)

import sqlalchemy
from boltons.iterutils import remap
from pydantic import BaseModel
from social_core.storage import (
    AssociationMixin,
    CodeMixin,
    NonceMixin,
    PartialMixin,
    UserMixin,
)
from sqlalchemy import (
    alias,
    and_,
    asc,
    BigInteger,
    bindparam,
    Boolean,
    case,
    Column,
    column,
    DateTime,
    delete,
    desc,
    event,
    false,
    ForeignKey,
    func,
    Index,
    inspect,
    Integer,
    join,
    MetaData,
    not_,
    Numeric,
    or_,
    PrimaryKeyConstraint,
    select,
    String,
    Table,
    TEXT,
    Text,
    text,
    true,
    tuple_,
    type_coerce,
    Unicode,
    UniqueConstraint,
    update,
    VARCHAR,
)
from sqlalchemy.exc import (
    CompileError,
    OperationalError,
)
from sqlalchemy.ext import hybrid
from sqlalchemy.ext.associationproxy import (
    association_proxy,
    AssociationProxy,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import (
    aliased,
    column_property,
    DeclarativeBase,
    deferred,
    joinedload,
    Mapped,
    mapped_column,
    object_session,
    Query,
    reconstructor,
    registry,
    relationship,
)
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.collections import attribute_keyed_dict
from sqlalchemy.sql import exists
from sqlalchemy.sql.expression import FromClause
from typing_extensions import (
    Literal,
    Protocol,
    TypeAlias,
    TypedDict,
)

import galaxy.exceptions
import galaxy.model.metadata
import galaxy.model.tags
import galaxy.security.passwords
import galaxy.util
from galaxy.files.templates import (
    FileSourceConfiguration,
    FileSourceTemplate,
    template_to_configuration as file_source_template_to_configuration,
)
from galaxy.model.base import (
    ensure_object_added_to_session,
    transaction,
)
from galaxy.model.custom_types import (
    DoubleEncodedJsonType,
    JSONType,
    MetadataType,
    MutableJSONType,
    TrimmedString,
    UUIDType,
)
from galaxy.model.database_object_names import NAMING_CONVENTION
from galaxy.model.item_attrs import (
    get_item_annotation_str,
    UsesAnnotations,
)
from galaxy.model.orm.now import now
from galaxy.model.orm.util import add_object_to_object_session
from galaxy.objectstore.templates import (
    ObjectStoreConfiguration,
    ObjectStoreTemplate,
    template_to_configuration as object_store_template_to_configuration,
)
from galaxy.schema.invocation import (
    InvocationCancellationUserRequest,
    InvocationState,
    InvocationStepState,
)
from galaxy.schema.schema import (
    DatasetCollectionPopulatedState,
    DatasetState,
    DatasetValidatedState,
    InvocationsStateCounts,
    JobState,
    ToolRequestState,
)
from galaxy.schema.workflow.comments import WorkflowCommentModel
from galaxy.security import get_permitted_actions
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.security.validate_user_input import validate_password_str
from galaxy.util import (
    directory_hash_id,
    enum_values,
    hex_to_lowercase_alphanum,
    listify,
    ready_name_for_url,
    unicodify,
    unique_id,
)
from galaxy.util.config_templates import (
    EnvironmentDict,
    ImplicitConfigurationParameters,
    SecretsDict,
    Template as ConfigTemplate,
    TemplateEnvironment,
)
from galaxy.util.dictifiable import (
    dict_for,
    Dictifiable,
)
from galaxy.util.form_builder import (
    AddressField,
    CheckboxField,
    HistoryField,
    PasswordField,
    SelectField,
    TextArea,
    TextField,
    WorkflowField,
    WorkflowMappingField,
)
from galaxy.util.hash_util import (
    HashFunctionNameEnum,
    md5_hash_str,
    new_insecure_hash,
)
from galaxy.util.json import safe_loads
from galaxy.util.sanitize_html import sanitize_html

if TYPE_CHECKING:
    from galaxy.objectstore import (
        BaseObjectStore,
        ObjectStorePopulator,
    )
    from galaxy.schema.invocation import InvocationMessageUnion

log = logging.getLogger(__name__)

_datatypes_registry = None

STR_TO_STR_DICT = Dict[str, str]


class ConfigurationTemplateEnvironmentSecret(TypedDict):
    name: str
    type: Literal["secret"]
    vault_key: str


class ConfigurationTemplateEnvironmentVariable(TypedDict):
    name: str
    type: Literal["variable"]
    variable: str


CONFIGURATION_TEMPLATE_ENVIRONMENT_ENTRY = Union[
    ConfigurationTemplateEnvironmentSecret, ConfigurationTemplateEnvironmentVariable
]
CONFIGURATION_TEMPLATE_ENVIRONMENT = List[CONFIGURATION_TEMPLATE_ENVIRONMENT_ENTRY]
CONFIGURATION_TEMPLATE_CONFIGURATION_VALUE_TYPE = Union[str, bool, int]
CONFIGURATION_TEMPLATE_CONFIGURATION_VARIABLES_TYPE = Dict[str, CONFIGURATION_TEMPLATE_CONFIGURATION_VALUE_TYPE]
CONFIGURATION_TEMPLATE_CONFIGURATION_SECRET_NAMES_TYPE = List[str]
CONFIGURATION_TEMPLATE_DEFINITION_TYPE = Dict[str, Any]


class TransformAction(TypedDict):
    action: str


TRANSFORM_ACTIONS = List[TransformAction]

mapper_registry = registry(
    type_annotation_map={
        Optional[STR_TO_STR_DICT]: JSONType,
        Optional[TRANSFORM_ACTIONS]: MutableJSONType,
        Optional[CONFIGURATION_TEMPLATE_CONFIGURATION_VARIABLES_TYPE]: JSONType,
        Optional[CONFIGURATION_TEMPLATE_CONFIGURATION_SECRET_NAMES_TYPE]: JSONType,
        Optional[CONFIGURATION_TEMPLATE_DEFINITION_TYPE]: JSONType,
        Optional[CONFIGURATION_TEMPLATE_ENVIRONMENT]: JSONType,
    },
)

# When constructing filters with in for a fixed set of ids, maximum
# number of items to place in the IN statement. Different databases
# are going to have different limits so it is likely best to not let
# this be unlimited - filter in Python if over this limit.
MAX_IN_FILTER_LENGTH = 100

# The column sizes for job metrics. Note: changing these values does not change the column sizes, a migration must be
# performed to do that.
JOB_METRIC_MAX_LENGTH = 1023
JOB_METRIC_PRECISION = 26
JOB_METRIC_SCALE = 7
# Tags that get automatically propagated from inputs to outputs when running jobs.
AUTO_PROPAGATED_TAGS = ["name"]
YIELD_PER_ROWS = 100
CANNOT_SHARE_PRIVATE_DATASET_MESSAGE = "Attempting to share a non-shareable dataset."


if TYPE_CHECKING:
    from galaxy.datatypes.data import Data
    from galaxy.tools import DefaultToolState
    from galaxy.workflow.modules import WorkflowModule

    class _HasTable:
        table: FromClause
        __table__: FromClause

else:
    _HasTable = object


def get_uuid(uuid: Optional[Union[UUID, str]] = None) -> UUID:
    if isinstance(uuid, UUID):
        return uuid
    if not uuid:
        return uuid4()
    return UUID(str(uuid))


class Base(DeclarativeBase, _HasTable):
    __abstract__ = True
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    mapper_registry.metadata = metadata
    registry = mapper_registry

    @classmethod
    def __declare_last__(cls):
        cls.table = cls.__table__


class RepresentById:
    id: Mapped[int]

    def __repr__(self):
        try:
            r = f"<galaxy.model.{self.__class__.__name__}({cached_id(self)}) at {hex(id(self))}>"
        except Exception:
            r = object.__repr__(self)
            log.exception("Caught exception attempting to generate repr for: %s", r)
        return r


class NoConverterException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ConverterDependencyException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def _get_datatypes_registry():
    if _datatypes_registry is None:
        raise Exception(
            "galaxy.model.set_datatypes_registry must be called before performing certain DatasetInstance operations."
        )
    return _datatypes_registry


def set_datatypes_registry(d_registry):
    """
    Set up datatypes_registry
    """
    global _datatypes_registry
    _datatypes_registry = d_registry


class HasTags:
    dict_collection_visible_keys = ["tags"]
    dict_element_visible_keys = ["tags"]

    def to_dict(self, *args, **kwargs):
        rval = super().to_dict(*args, **kwargs)
        rval["tags"] = self.make_tag_string_list()
        return rval

    def make_tag_string_list(self):
        # add tags string list
        tags_str_list = []
        for tag in self.tags:
            tag_str = tag.user_tname
            if tag.value is not None:
                tag_str += f":{tag.user_value}"
            tags_str_list.append(tag_str)
        return tags_str_list

    def copy_tags_from(self, target_user, source):
        for source_tag_assoc in source.tags:
            new_tag_assoc = source_tag_assoc.copy()
            new_tag_assoc.user = target_user
            self.tags.append(new_tag_assoc)

    @property
    def auto_propagated_tags(self):
        return [t for t in self.tags if t.user_tname in AUTO_PROPAGATED_TAGS]


class SerializeFilesHandler(Protocol):
    def serialize_files(self, dataset: "DatasetInstance", as_dict: Dict[str, Any]) -> None:
        pass


class SerializationOptions:
    def __init__(
        self,
        for_edit: bool,
        serialize_dataset_objects: Optional[bool] = None,
        serialize_files_handler: Optional[SerializeFilesHandler] = None,
        strip_metadata_files: Optional[bool] = None,
    ) -> None:
        self.for_edit = for_edit
        if serialize_dataset_objects is None:
            serialize_dataset_objects = for_edit
        self.serialize_dataset_objects = serialize_dataset_objects
        self.serialize_files_handler = serialize_files_handler
        if strip_metadata_files is None:
            # If we're editing datasets - keep MetadataFile(s) in tact. For pure export
            # expect metadata tool to be rerun.
            strip_metadata_files = not for_edit
        self.strip_metadata_files = strip_metadata_files

    def attach_identifier(self, id_encoder, obj, ret_val):
        if self.for_edit and obj.id:
            ret_val["id"] = obj.id
        elif obj.id:
            ret_val["encoded_id"] = id_encoder.encode_id(obj.id, kind="model_export")
        else:
            if not hasattr(obj, "temp_id"):
                obj.temp_id = uuid4().hex
            ret_val["encoded_id"] = obj.temp_id

    def get_identifier(self, id_encoder, obj):
        if self.for_edit and obj.id:
            return obj.id
        elif obj.id:
            return id_encoder.encode_id(obj.id, kind="model_export")
        else:
            if not hasattr(obj, "temp_id"):
                obj.temp_id = uuid4().hex
            return obj.temp_id

    def get_identifier_for_id(self, id_encoder, obj_id):
        if self.for_edit and obj_id:
            return obj_id
        elif obj_id:
            return id_encoder.encode_id(obj_id, kind="model_export")
        else:
            raise NotImplementedError()

    def serialize_files(self, dataset, as_dict):
        if self.serialize_files_handler is not None:
            self.serialize_files_handler.serialize_files(dataset, as_dict)


class Serializable(RepresentById):
    def serialize(
        self, id_encoder: IdEncodingHelper, serialization_options: SerializationOptions, for_link: bool = False
    ) -> Dict[str, Any]:
        """Serialize model for a re-population in (potentially) another Galaxy instance."""
        if for_link:
            rval = dict_for(self)
            serialization_options.attach_identifier(id_encoder, self, rval)
            return rval
        return self._serialize(id_encoder, serialization_options)

    @abc.abstractmethod
    def _serialize(self, id_encoder: IdEncodingHelper, serialization_options: SerializationOptions) -> Dict[str, Any]:
        """Serialize model for a re-population in (potentially) another Galaxy instance."""


class HasName:
    def get_display_name(self):
        """
        These objects have a name attribute can be either a string or a unicode
        object. If string, convert to unicode object assuming 'utf-8' format.
        """
        name = self.name
        name = unicodify(name, "utf-8")
        return name


class UsesCreateAndUpdateTime:
    update_time: Mapped[Optional[datetime]]

    @property
    def seconds_since_updated(self):
        update_time = self.update_time or now()  # In case not yet flushed
        return (now() - update_time).total_seconds()

    @property
    def seconds_since_created(self):
        create_time = self.create_time or now()  # In case not yet flushed
        return (now() - create_time).total_seconds()

    def update(self):
        self.update_time = now()


class WorkerProcess(Base, UsesCreateAndUpdateTime):
    __tablename__ = "worker_process"
    __table_args__ = (UniqueConstraint("server_name", "hostname"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    server_name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    hostname: Mapped[Optional[str]] = mapped_column(String(255))
    pid: Mapped[Optional[int]]
    update_time: Mapped[Optional[datetime]] = mapped_column(default=now, onupdate=now)


def cached_id(galaxy_model_object):
    """Get model object id attribute without a firing a database query.

    Useful to fetching the id of a typical Galaxy model object after a flush,
    where SA is going to mark the id attribute as unloaded but we know the id
    is immutable and so we can use the database identity to fetch.

    With Galaxy's default SA initialization - any flush marks all attributes as
    unloaded - even objects completely unrelated to the flushed changes and
    even attributes we know to be immutable like id. See test_galaxy_mapping.py
    for verification of this behavior. This method is a workaround that uses
    the fact that we know all Galaxy objects use the id attribute as identity
    and SA internals (_sa_instance_state) to infer the previously loaded ID
    value. I tried digging into the SA internals extensively and couldn't find
    a way to get the previously loaded values after a flush to allow a
    generalization of this for other attributes.
    """
    if hasattr(galaxy_model_object, "_sa_instance_state"):
        identity = galaxy_model_object._sa_instance_state.identity
        if identity:
            assert len(identity) == 1
            return identity[0]

    return galaxy_model_object.id


class JobLike:
    MAX_NUMERIC = 10 ** (JOB_METRIC_PRECISION - JOB_METRIC_SCALE) - 1

    def _init_metrics(self):
        self.text_metrics = []
        self.numeric_metrics = []

    def add_metric(self, plugin, metric_name, metric_value):
        plugin = unicodify(plugin, "utf-8")
        metric_name = unicodify(metric_name, "utf-8")
        number = isinstance(metric_value, numbers.Number)
        if number and int(metric_value) <= JobLike.MAX_NUMERIC:
            metric = self._numeric_metric(plugin, metric_name, metric_value)
            self.numeric_metrics.append(metric)
        elif number:
            log.warning(
                "Cannot store metric due to database column overflow (max: %s): %s: %s",
                JobLike.MAX_NUMERIC,
                metric_name,
                metric_value,
            )
        else:
            metric_value = unicodify(metric_value, "utf-8")
            if len(metric_value) > (JOB_METRIC_MAX_LENGTH - 1):
                # Truncate these values - not needed with sqlite
                # but other backends must need it.
                metric_value = metric_value[: (JOB_METRIC_MAX_LENGTH - 1)]
            metric = self._text_metric(plugin, metric_name, metric_value)
            self.text_metrics.append(metric)

    @property
    def metrics(self):
        # TODO: Make iterable, concatenate with chain
        return self.text_metrics + self.numeric_metrics

    def set_streams(self, tool_stdout, tool_stderr, job_stdout=None, job_stderr=None, job_messages=None):
        def shrink_and_unicodify(what, stream):
            if stream and len(stream) > galaxy.util.DATABASE_MAX_STRING_SIZE:
                log.info(
                    "%s for %s %d is greater than %s, only a portion will be logged to database",
                    what,
                    type(self),
                    self.id,
                    galaxy.util.DATABASE_MAX_STRING_SIZE_PRETTY,
                )
            return galaxy.util.shrink_and_unicodify(stream)

        self.tool_stdout = shrink_and_unicodify("tool_stdout", tool_stdout)
        self.tool_stderr = shrink_and_unicodify("tool_stderr", tool_stderr)
        if job_stdout is not None:
            self.job_stdout = shrink_and_unicodify("job_stdout", job_stdout)
        else:
            self.job_stdout = None

        if job_stderr is not None:
            self.job_stderr = shrink_and_unicodify("job_stderr", job_stderr)
        else:
            self.job_stderr = None

        if job_messages is not None:
            self.job_messages = job_messages

    def log_str(self):
        extra = ""
        if (safe_id := getattr(self, "id", None)) is not None:
            extra += f"id={safe_id}"
        else:
            extra += "unflushed"

        return f"{self.__class__.__name__}[{extra},tool_id={self.tool_id}]"

    @property
    def stdout(self):
        stdout = self.tool_stdout or ""
        if self.job_stdout:
            stdout += f"\n{self.job_stdout}"
        return stdout

    @stdout.setter
    def stdout(self, stdout):
        raise NotImplementedError("Attempt to set stdout, must set tool_stdout or job_stdout")

    @property
    def stderr(self):
        stderr = self.tool_stderr or ""
        if self.job_stderr:
            stderr += f"\n{self.job_stderr}"
        return stderr

    @stderr.setter
    def stderr(self, stderr):
        raise NotImplementedError("Attempt to set stdout, must set tool_stderr or job_stderr")


UNIQUE_DATASET_USER_USAGE = """
WITH per_user_histories AS
(
    SELECT id
    FROM history
    WHERE user_id = :id
        AND NOT purged
),
per_hist_hdas AS (
    SELECT DISTINCT dataset_id
    FROM history_dataset_association
    WHERE NOT purged
        AND history_id IN (SELECT id FROM per_user_histories)
)
SELECT COALESCE(SUM(COALESCE(dataset.total_size, dataset.file_size, 0)), 0)
FROM dataset
LEFT OUTER JOIN library_dataset_dataset_association ON dataset.id = library_dataset_dataset_association.dataset_id
WHERE dataset.id IN (SELECT dataset_id FROM per_hist_hdas)
    AND library_dataset_dataset_association.id IS NULL
    {and_dataset_condition}
"""


def calculate_user_disk_usage_statements(user_id, quota_source_map, for_sqlite=False):
    """Standalone function so can be reused for postgres directly in pgcleanup.py."""
    statements = []
    default_quota_enabled = quota_source_map.default_quota_enabled
    default_exclude_ids = quota_source_map.default_usage_excluded_ids()
    default_cond = "dataset.object_store_id IS NULL" if default_quota_enabled and default_exclude_ids else ""
    exclude_cond = "dataset.object_store_id NOT IN :exclude_object_store_ids" if default_exclude_ids else ""
    use_or = " OR " if (default_cond != "" and exclude_cond != "") else ""
    default_usage_dataset_condition = f"{default_cond} {use_or} {exclude_cond}"
    if default_usage_dataset_condition.strip():
        default_usage_dataset_condition = f"AND ( {default_usage_dataset_condition} )"
    default_usage = UNIQUE_DATASET_USER_USAGE.format(and_dataset_condition=default_usage_dataset_condition)
    default_usage = f"""
UPDATE galaxy_user SET disk_usage = ({default_usage})
WHERE id = :id
"""
    params = {"id": user_id}
    if default_exclude_ids:
        params["exclude_object_store_ids"] = default_exclude_ids
    statements.append((default_usage, params))
    source = quota_source_map.ids_per_quota_source()
    # TODO: Merge a lot of these settings together by generating a temp table for
    # the object_store_id to quota_source_label into a temp table of values
    for quota_source_label, object_store_ids in source.items():
        label_usage = UNIQUE_DATASET_USER_USAGE.format(
            and_dataset_condition="AND ( dataset.object_store_id IN :include_object_store_ids )"
        )
        if for_sqlite:
            # hacky alternative for older sqlite
            statement = f"""
WITH new (user_id, quota_source_label, disk_usage) AS (
    VALUES(:id, :label, ({label_usage}))
)
INSERT OR REPLACE INTO user_quota_source_usage (id, user_id, quota_source_label, disk_usage)
SELECT old.id, new.user_id, new.quota_source_label, new.disk_usage
FROM new
    LEFT JOIN user_quota_source_usage AS old
        ON new.user_id = old.user_id
            AND new.quota_source_label = old.quota_source_label
"""
        else:
            statement = f"""
INSERT INTO user_quota_source_usage(user_id, quota_source_label, disk_usage)
VALUES(:id, :label, ({label_usage}))
ON CONFLICT
ON constraint uqsu_unique_label_per_user
DO UPDATE SET disk_usage = excluded.disk_usage
"""
        statements.append(
            (statement, {"id": user_id, "label": quota_source_label, "include_object_store_ids": object_store_ids})
        )

    params = {"id": user_id}
    source_labels = list(source.keys())
    if len(source_labels) > 0:
        clean_old_statement = """
DELETE FROM user_quota_source_usage
WHERE user_id = :id AND quota_source_label NOT IN :labels
"""
        params["labels"] = source_labels
    else:
        clean_old_statement = """
DELETE FROM user_quota_source_usage
WHERE user_id = :id AND quota_source_label IS NOT NULL
"""
    statements.append((clean_old_statement, params))
    return statements


UNIQUE_DATASET_USER_USAGE_PER_OBJECTSTORE = """
WITH per_user_histories AS
(
    SELECT id
    FROM history
    WHERE user_id = :id
        AND NOT purged
),
per_hist_hdas AS (
    SELECT DISTINCT dataset_id
    FROM history_dataset_association
    WHERE NOT purged
        AND history_id IN (SELECT id FROM per_user_histories)
)
SELECT SUM(COALESCE(dataset.total_size, dataset.file_size, 0)) as usage, dataset.object_store_id
FROM dataset
LEFT OUTER JOIN library_dataset_dataset_association ON dataset.id = library_dataset_dataset_association.dataset_id
WHERE dataset.id IN (SELECT dataset_id FROM per_hist_hdas)
    AND library_dataset_dataset_association.id IS NULL
GROUP BY dataset.object_store_id
"""


def calculate_disk_usage_per_objectstore(sa_session, user_id: int):
    statement = UNIQUE_DATASET_USER_USAGE_PER_OBJECTSTORE
    params = {"id": user_id}
    return sa_session.execute(text(statement), params).all()


# move these to galaxy.schema.schema once galaxy-data depends on
# galaxy-schema.
class UserQuotaBasicUsage(BaseModel):
    quota_source_label: Optional[str] = None
    total_disk_usage: float


class UserQuotaUsage(UserQuotaBasicUsage):
    quota_percent: Optional[float] = None
    quota_bytes: Optional[int] = None
    quota: Optional[str] = None


class UserObjectstoreUsage(BaseModel):
    object_store_id: str
    total_disk_usage: float


class User(Base, Dictifiable, RepresentById):
    """
    Data for a Galaxy user or admin and relations to their
    histories, credentials, and roles.
    """

    use_pbkdf2 = True
    bootstrap_admin_user = False
    # api_keys: 'List[APIKeys]'  already declared as relationship()

    __tablename__ = "galaxy_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    email: Mapped[str] = mapped_column(TrimmedString(255), index=True, unique=True)
    username: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True, unique=True)
    password: Mapped[str] = mapped_column(TrimmedString(255))
    last_password_change: Mapped[Optional[datetime]] = mapped_column(default=now)
    external: Mapped[Optional[bool]] = mapped_column(default=False)
    form_values_id: Mapped[Optional[int]] = mapped_column(ForeignKey("form_values.id"), index=True)
    preferred_object_store_id: Mapped[str] = mapped_column(String(255), nullable=True)
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    purged: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    disk_usage: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 0), index=True)
    # Column("person_metadata", JSONType),  # TODO: add persistent, configurable metadata rep for workflow creator
    active: Mapped[bool] = mapped_column(index=True, default=True)
    activation_token: Mapped[Optional[str]] = mapped_column(TrimmedString(64), index=True)

    addresses: Mapped[List["UserAddress"]] = relationship(
        back_populates="user", order_by=lambda: desc(UserAddress.update_time)
    )
    custos_auth: Mapped[List["CustosAuthnzToken"]] = relationship(back_populates="user")
    chat_exchanges: Mapped[List["ChatExchange"]] = relationship(back_populates="user")
    default_permissions: Mapped[List["DefaultUserPermissions"]] = relationship(back_populates="user")
    groups: Mapped[List["UserGroupAssociation"]] = relationship(back_populates="user")
    histories: Mapped[List["History"]] = relationship(
        back_populates="user", order_by=lambda: desc(History.update_time)  # type: ignore[has-type]
    )
    active_histories: Mapped[List["History"]] = relationship(
        primaryjoin=(lambda: (History.user_id == User.id) & (not_(History.deleted)) & (not_(History.archived))),
        viewonly=True,
        order_by=lambda: desc(History.update_time),  # type: ignore[has-type]
    )
    galaxy_sessions: Mapped[List["GalaxySession"]] = relationship(
        back_populates="user", order_by=lambda: desc(GalaxySession.update_time)
    )
    object_stores: Mapped[List["UserObjectStore"]] = relationship(back_populates="user")
    file_sources: Mapped[List["UserFileSource"]] = relationship(back_populates="user")
    quotas: Mapped[List["UserQuotaAssociation"]] = relationship(back_populates="user")
    quota_source_usages: Mapped[List["UserQuotaSourceUsage"]] = relationship(back_populates="user")
    social_auth: Mapped[List["UserAuthnzToken"]] = relationship(back_populates="user")
    stored_workflow_menu_entries: Mapped[List["StoredWorkflowMenuEntry"]] = relationship(
        primaryjoin=(
            lambda: (StoredWorkflowMenuEntry.user_id == User.id)
            & (StoredWorkflowMenuEntry.stored_workflow_id == StoredWorkflow.id)
            & not_(StoredWorkflow.deleted)
        ),
        back_populates="user",
        cascade="all, delete-orphan",
        collection_class=ordering_list("order_index"),
    )
    _preferences: Mapped[Dict[str, "UserPreference"]] = relationship(collection_class=attribute_keyed_dict("name"))
    values: Mapped[List["FormValues"]] = relationship(primaryjoin=(lambda: User.form_values_id == FormValues.id))
    # Add type hint (will this work w/SA?)
    api_keys: Mapped[List["APIKeys"]] = relationship(
        back_populates="user",
        order_by=lambda: desc(APIKeys.create_time),
        primaryjoin=(
            lambda: and_(
                User.id == APIKeys.user_id,
                not_(APIKeys.deleted == true()),
            )
        ),
    )
    data_manager_histories: Mapped[List["DataManagerHistoryAssociation"]] = relationship(back_populates="user")
    roles: Mapped[List["UserRoleAssociation"]] = relationship(back_populates="user")
    stored_workflows: Mapped[List["StoredWorkflow"]] = relationship(
        back_populates="user",
        primaryjoin=(lambda: User.id == StoredWorkflow.user_id),
    )
    all_notifications: Mapped[List["UserNotificationAssociation"]] = relationship(back_populates="user")

    preferences: AssociationProxy[Any]

    # attributes that will be accessed and returned when calling to_dict( view='collection' )
    dict_collection_visible_keys = ["id", "email", "username", "deleted", "active", "last_password_change"]
    # attributes that will be accessed and returned when calling to_dict( view='element' )
    dict_element_visible_keys = [
        "id",
        "email",
        "username",
        "total_disk_usage",
        "nice_total_disk_usage",
        "deleted",
        "active",
        "last_password_change",
        "preferred_object_store_id",
    ]

    def __init__(self, email=None, password=None, username=None):
        self.email = email
        self.password = password
        self.external = False
        self.deleted = False
        self.purged = False
        self.active = False
        self.username = username

    def get_user_data_tables(self, data_table: str):
        session = object_session(self)
        assert session
        metadata_select = (
            select(HistoryDatasetAssociation)
            .join(Dataset)
            .join(History)
            .where(
                HistoryDatasetAssociation.deleted == false(),
                HistoryDatasetAssociation.extension == "data_manager_json",
                History.user_id == self.id,
                Dataset.state == "ok",
                # excludes data manager runs that actually populated tables.
                # maybe track this formally by creating a different datatype for bundles ?
                Dataset.total_size != Dataset.file_size,
                HistoryDatasetAssociation._metadata.contains(data_table),
            )
            .order_by(HistoryDatasetAssociation.id)
        )
        return session.execute(metadata_select).scalars().all()

    @property
    def extra_preferences(self):
        data = defaultdict(lambda: None)
        if extra_user_preferences := self.preferences.get("extra_user_preferences"):
            try:
                data.update(json.loads(extra_user_preferences))
            except Exception:
                pass
        return data

    def set_password_cleartext(self, cleartext):
        """
        Set user password to the digest of `cleartext`.
        """
        if message := validate_password_str(cleartext):
            raise Exception(f"Invalid password: {message}")
        if User.use_pbkdf2:
            self.password = galaxy.security.passwords.hash_password(cleartext)
        else:
            self.password = new_insecure_hash(text_type=cleartext)
        self.last_password_change = now()

    def set_random_password(self, length=16):
        """
        Sets user password to a random string of the given length.
        :return: void
        """
        self.set_password_cleartext(
            "".join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(length))
        )

    def check_password(self, cleartext):
        """
        Check if `cleartext` matches user password when hashed.
        """
        return galaxy.security.passwords.check_password(cleartext, self.password)

    def system_user_pwent(self, real_system_username):
        """
        Gives the system user pwent entry based on e-mail or username depending
        on the value in real_system_username
        """
        if real_system_username == "user_email":
            username = self.email.split("@")[0]
        elif real_system_username == "username":
            username = self.username
        else:
            username = real_system_username
        try:
            return pwd.getpwnam(username)
        except Exception:
            log.exception(f"Error getting the password database entry for user {username}")
            raise

    def all_roles(self):
        """
        Return a unique list of Roles associated with this user or any of their groups.
        """
        try:
            db_session = object_session(self)
            user = (
                db_session.query(User)
                .filter_by(id=self.id)  # don't use get, it will use session variant.
                .options(
                    joinedload(User.roles),
                    joinedload(User.roles.role),
                    joinedload(User.groups),
                    joinedload(User.groups.group),
                    joinedload(User.groups.group.roles),
                    joinedload(User.groups.group.roles.role),
                )
                .one()
            )
        except Exception:
            # If not persistent user, just use models normaly and
            # skip optimizations...
            user = self

        roles = [ura.role for ura in user.roles]
        for group in [uga.group for uga in user.groups]:
            for role in [gra.role for gra in group.roles]:
                if role not in roles:
                    roles.append(role)
        return roles

    def all_roles_exploiting_cache(self):
        """ """
        roles = [ura.role for ura in self.roles]
        for group in [uga.group for uga in self.groups]:
            for role in [gra.role for gra in group.roles]:
                if role not in roles:
                    roles.append(role)
        return roles

    def get_disk_usage(self, nice_size=False, quota_source_label=None):
        """
        Return byte count of disk space used by user or a human-readable
        string if `nice_size` is `True`.
        """
        if quota_source_label is None:
            rval = 0
            if self.disk_usage is not None:
                rval = self.disk_usage
        else:
            statement = """
SELECT DISK_USAGE
FROM user_quota_source_usage
WHERE user_id = :user_id and quota_source_label = :label
"""
            sa_session = object_session(self)
            params = {
                "user_id": self.id,
                "label": quota_source_label,
            }
            row = sa_session.execute(text(statement), params).fetchone()
            if row is not None:
                rval = row[0]
            else:
                rval = 0
        if nice_size:
            rval = galaxy.util.nice_size(rval)
        return rval

    def set_disk_usage(self, bytes):
        """
        Manually set the disk space used by a user to `bytes`.
        """
        self.disk_usage = bytes

    total_disk_usage = property(get_disk_usage, set_disk_usage)

    def adjust_total_disk_usage(self, amount, quota_source_label):
        assert amount is not None
        if amount != 0:
            if quota_source_label is None:
                self.disk_usage = (self.disk_usage or 0) + amount
            else:
                # else would work on newer sqlite - 3.24.0
                engine = object_session(self).bind
                if "sqlite" in engine.dialect.name:
                    # hacky alternative for older sqlite
                    statement = """
WITH new (user_id, quota_source_label) AS ( VALUES(:user_id, :label) )
INSERT OR REPLACE INTO user_quota_source_usage (id, user_id, quota_source_label, disk_usage)
SELECT old.id, new.user_id, new.quota_source_label, COALESCE(old.disk_usage + :amount, :amount)
FROM new LEFT JOIN user_quota_source_usage AS old ON new.user_id = old.user_id AND NEW.quota_source_label = old.quota_source_label;
"""
                else:
                    statement = """
INSERT INTO user_quota_source_usage(user_id, disk_usage, quota_source_label)
VALUES(:user_id, :amount, :label)
ON CONFLICT
    ON constraint uqsu_unique_label_per_user
    DO UPDATE SET disk_usage = user_quota_source_usage.disk_usage + :amount
"""
                statement = text(statement)
                params = {
                    "user_id": self.id,
                    "amount": int(amount),
                    "label": quota_source_label,
                }
                with engine.connect() as conn, conn.begin():
                    conn.execute(statement, params)

    def _get_social_auth(self, provider_backend):
        if not self.social_auth:
            return None
        for auth in self.social_auth:
            if auth.provider == provider_backend and auth.extra_data:
                return auth
        return None

    def _get_custos_auth(self, provider_backend):
        if not self.custos_auth:
            return None
        for auth in self.custos_auth:
            if auth.provider == provider_backend and auth.refresh_token:
                return auth
        return None

    def get_oidc_tokens(self, provider_backend):
        tokens = {"id": None, "access": None, "refresh": None}
        auth = self._get_social_auth(provider_backend)
        if auth:
            tokens["access"] = auth.extra_data.get("access_token", None)
            tokens["refresh"] = auth.extra_data.get("refresh_token", None)
            tokens["id"] = auth.extra_data.get("id_token", None)
            return tokens

        # no social auth found, check custos auth
        auth = self._get_custos_auth(provider_backend)
        if auth:
            tokens["access"] = auth.access_token
            tokens["refresh"] = auth.refresh_token
            tokens["id"] = auth.id_token

        return tokens

    @property
    def nice_total_disk_usage(self):
        """
        Return byte count of disk space used in a human-readable string.
        """
        return self.get_disk_usage(nice_size=True)

    def calculate_disk_usage_default_source(self, object_store):
        """
        Return byte count total of disk space used by all non-purged, non-library
        HDAs in non-purged histories assigned to default quota source.
        """
        # only used in set_user_disk_usage.py
        assert object_store is not None
        quota_source_map = object_store.get_quota_source_map()
        default_quota_enabled = quota_source_map.default_quota_enabled
        exclude_objectstore_ids = quota_source_map.default_usage_excluded_ids()
        default_cond = "dataset.object_store_id IS NULL OR" if default_quota_enabled and exclude_objectstore_ids else ""
        default_usage_dataset_condition = (
            f"AND ( {default_cond} dataset.object_store_id NOT IN :exclude_object_store_ids )"
            if exclude_objectstore_ids
            else ""
        )
        default_usage = UNIQUE_DATASET_USER_USAGE.format(and_dataset_condition=default_usage_dataset_condition)
        sql_calc = text(default_usage)
        params = {"id": self.id}
        bindparams = [bindparam("id")]
        if exclude_objectstore_ids:
            params["exclude_object_store_ids"] = exclude_objectstore_ids
            bindparams.append(bindparam("exclude_object_store_ids", expanding=True))
        sql_calc = sql_calc.bindparams(*bindparams)
        sa_session = object_session(self)
        usage = sa_session.scalar(sql_calc, params)
        return usage

    def calculate_and_set_disk_usage(self, object_store):
        """
        Calculates and sets user disk usage.
        """
        self._calculate_or_set_disk_usage(object_store=object_store)

    def _calculate_or_set_disk_usage(self, object_store):
        """
        Utility to calculate and return the disk usage.  If dryrun is False,
        the new value is set immediately.
        """
        assert object_store is not None
        quota_source_map = object_store.get_quota_source_map()
        sa_session = object_session(self)
        for_sqlite = "sqlite" in sa_session.bind.dialect.name
        statements = calculate_user_disk_usage_statements(self.id, quota_source_map, for_sqlite)
        for sql, args in statements:
            statement = text(sql)
            binds = []
            for key, _ in args.items():
                expand_binding = key.endswith("s")
                binds.append(bindparam(key, expanding=expand_binding))
            statement = statement.bindparams(*binds)
            sa_session.execute(statement, args)
            # expire user.disk_usage so sqlalchemy knows to ignore
            # the existing value - we're setting it in raw SQL for
            # performance reasons and bypassing object properties.
            sa_session.expire(self, ["disk_usage"])
        with transaction(sa_session):
            sa_session.commit()

    @staticmethod
    def user_template_environment(user: Optional["User"]):
        """

        >>> env = User.user_template_environment(None)
        >>> env['__user_email__']
        'Anonymous'
        >>> env['__user_id__']
        'Anonymous'
        >>> user = User('foo@example.com')
        >>> user.id = 6
        >>> user.username = 'foo2'
        >>> env = User.user_template_environment(user)
        >>> env['__user_id__']
        '6'
        >>> env['__user_name__']
        'foo2'
        """
        if user:
            user_id = f"{user.id}"
            user_email = str(user.email)
            user_name = str(user.username)
        else:
            user = None
            user_id = "Anonymous"
            user_email = "Anonymous"
            user_name = "Anonymous"
        environment: Dict[str, Any] = {}
        environment["__user__"] = user
        environment["__user_id__"] = environment["userId"] = user_id
        environment["__user_email__"] = environment["userEmail"] = user_email
        environment["__user_name__"] = user_name
        return environment

    @staticmethod
    def expand_user_properties(user, in_string: str):
        """ """
        environment = User.user_template_environment(user)
        return Template(in_string).safe_substitute(environment)

    # above templating is for Cheetah in tools where we discouraged user details from being exposed.
    # the following templating if user details in Jinja for object stores and file sources where user
    # details are critical and documented.
    def config_template_details(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "email": self.email,
            "id": self.id,
        }

    def is_active(self):
        return self.active

    def is_authenticated(self):
        # TODO: is required for python social auth (PSA); however, a user authentication is relative to the backend.
        # For instance, a user who is authenticated with Google, is not necessarily authenticated
        # with Amazon. Therefore, this function should also receive the backend and check if this
        # user is already authenticated on that backend or not. For now, returning always True
        # seems reasonable. Besides, this is also how a PSA example is implemented:
        # https://github.com/python-social-auth/social-examples/blob/master/example-cherrypy/example/db/user.py
        return True

    def attempt_create_private_role(self):
        session = object_session(self)
        role = Role(type=Role.types.PRIVATE)
        assoc = UserRoleAssociation(self, role)
        session.add(assoc)
        with transaction(session):
            session.commit()

    def dictify_objectstore_usage(self) -> List[UserObjectstoreUsage]:
        session = object_session(self)
        rows = calculate_disk_usage_per_objectstore(session, self.id)
        return [
            UserObjectstoreUsage(object_store_id=r.object_store_id, total_disk_usage=r.usage)
            for r in rows
            if r.object_store_id
        ]

    def dictify_usage(self, object_store=None) -> List[UserQuotaBasicUsage]:
        """Include object_store to include empty/unused usage info."""
        used_labels: Set[Union[str, None]] = set()
        rval: List[UserQuotaBasicUsage] = [
            UserQuotaBasicUsage(
                quota_source_label=None,
                total_disk_usage=float(self.disk_usage or 0),
            )
        ]
        used_labels.add(None)
        for quota_source_usage in self.quota_source_usages:
            label = quota_source_usage.quota_source_label
            rval.append(
                UserQuotaBasicUsage(
                    quota_source_label=label,
                    total_disk_usage=float(quota_source_usage.disk_usage),
                )
            )
            used_labels.add(label)

        if object_store is not None:
            for label in object_store.get_quota_source_map().ids_per_quota_source().keys():
                if label not in used_labels:
                    rval.append(
                        UserQuotaBasicUsage(
                            quota_source_label=label,
                            total_disk_usage=0.0,
                        )
                    )

        return rval

    def dictify_usage_for(self, quota_source_label: Optional[str]) -> UserQuotaBasicUsage:
        rval: UserQuotaBasicUsage
        if quota_source_label is None:
            rval = UserQuotaBasicUsage(
                quota_source_label=None,
                total_disk_usage=float(self.disk_usage or 0),
            )
        else:
            quota_source_usage = self.quota_source_usage_for(quota_source_label)
            if quota_source_usage is None:
                rval = UserQuotaBasicUsage(
                    quota_source_label=quota_source_label,
                    total_disk_usage=0.0,
                )
            else:
                rval = UserQuotaBasicUsage(
                    quota_source_label=quota_source_label,
                    total_disk_usage=float(quota_source_usage.disk_usage),
                )

        return rval

    def quota_source_usage_for(self, quota_source_label: Optional[str]) -> Optional["UserQuotaSourceUsage"]:
        for quota_source_usage in self.quota_source_usages:
            if quota_source_usage.quota_source_label == quota_source_label:
                return quota_source_usage
        return None

    def count_stored_workflow_user_assocs(self, stored_workflow) -> int:
        sq = select(StoredWorkflowUserShareAssociation).filter_by(user=self, stored_workflow=stored_workflow).subquery()
        stmt = select(func.count()).select_from(sq)
        session = object_session(self)
        assert session
        return session.scalar(stmt) or 0


class PasswordResetToken(Base):
    __tablename__ = "password_reset_token"

    token: Mapped[str] = mapped_column(String(32), primary_key=True, unique=True, index=True)
    expiration_time: Mapped[Optional[datetime]]
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    user: Mapped[Optional["User"]] = relationship()

    def __init__(self, user, token=None):
        if token:
            self.token = token
        else:
            self.token = unique_id()
        self.user = user
        self.expiration_time = now() + timedelta(hours=24)


class ToolSource(Base, Dictifiable, RepresentById):
    __tablename__ = "tool_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    hash: Mapped[Optional[str]] = mapped_column(Unicode(255))
    source: Mapped[dict] = mapped_column(JSONType)


class ToolRequest(Base, Dictifiable, RepresentById):
    __tablename__ = "tool_request"

    states: TypeAlias = ToolRequestState

    id: Mapped[int] = mapped_column(primary_key=True)
    tool_source_id: Mapped[int] = mapped_column(ForeignKey("tool_source.id"), index=True)
    history_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history.id"), index=True)
    request: Mapped[dict] = mapped_column(JSONType)
    state: Mapped[Optional[str]] = mapped_column(TrimmedString(32), index=True)
    state_message: Mapped[Optional[str]] = mapped_column(JSONType, index=True)

    tool_source: Mapped["ToolSource"] = relationship()
    history: Mapped[Optional["History"]] = relationship(back_populates="tool_requests")


class DynamicTool(Base, Dictifiable, RepresentById):
    __tablename__ = "dynamic_tool"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[Optional[Union[UUID, str]]] = mapped_column(UUIDType())
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(index=True, default=now, onupdate=now, nullable=True)
    tool_id: Mapped[Optional[str]] = mapped_column(Unicode(255))
    tool_version: Mapped[Optional[str]] = mapped_column(Unicode(255))
    tool_format: Mapped[Optional[str]] = mapped_column(Unicode(255))
    tool_path: Mapped[Optional[str]] = mapped_column(Unicode(255))
    tool_directory: Mapped[Optional[str]] = mapped_column(Unicode(255))
    hidden: Mapped[Optional[bool]] = mapped_column(default=True)
    active: Mapped[Optional[bool]] = mapped_column(default=True)
    value: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)

    dict_collection_visible_keys = ("id", "tool_id", "tool_format", "tool_version", "uuid", "active", "hidden")
    dict_element_visible_keys = ("id", "tool_id", "tool_format", "tool_version", "uuid", "active", "hidden")

    def __init__(self, active=True, hidden=True, **kwd):
        super().__init__(**kwd)
        self.active = active
        self.hidden = hidden
        _uuid = kwd.get("uuid")
        self.uuid = get_uuid(_uuid)


class BaseJobMetric(Base):
    __abstract__ = True

    def __init__(self, plugin, metric_name, metric_value):
        super().__init__()
        self.plugin = plugin
        self.metric_name = metric_name
        self.metric_value = metric_value


class JobMetricText(BaseJobMetric, RepresentById):
    __tablename__ = "job_metric_text"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    plugin: Mapped[Optional[str]] = mapped_column(Unicode(255))
    metric_name: Mapped[Optional[str]] = mapped_column(Unicode(255))
    metric_value: Mapped[Optional[str]] = mapped_column(Unicode(JOB_METRIC_MAX_LENGTH))


class JobMetricNumeric(BaseJobMetric, RepresentById):
    __tablename__ = "job_metric_numeric"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    plugin: Mapped[Optional[str]] = mapped_column(Unicode(255))
    metric_name: Mapped[Optional[str]] = mapped_column(Unicode(255))
    metric_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(JOB_METRIC_PRECISION, JOB_METRIC_SCALE))


class TaskMetricText(BaseJobMetric, RepresentById):
    __tablename__ = "task_metric_text"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("task.id"), index=True)
    plugin: Mapped[Optional[str]] = mapped_column(Unicode(255))
    metric_name: Mapped[Optional[str]] = mapped_column(Unicode(255))
    metric_value: Mapped[Optional[str]] = mapped_column(Unicode(JOB_METRIC_MAX_LENGTH))


class TaskMetricNumeric(BaseJobMetric, RepresentById):
    __tablename__ = "task_metric_numeric"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("task.id"), index=True)
    plugin: Mapped[Optional[str]] = mapped_column(Unicode(255))
    metric_name: Mapped[Optional[str]] = mapped_column(Unicode(255))
    metric_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(JOB_METRIC_PRECISION, JOB_METRIC_SCALE))


class IoDicts(NamedTuple):
    inp_data: Dict[str, Optional["DatasetInstance"]]
    out_data: Dict[str, "DatasetInstance"]
    out_collections: Dict[str, Union["DatasetCollectionInstance", "DatasetCollection"]]


class Job(Base, JobLike, UsesCreateAndUpdateTime, Dictifiable, Serializable):
    """
    A job represents a request to run a tool given input datasets, tool
    parameters, and output datasets.
    """

    __tablename__ = "job"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, index=True, nullable=True)
    history_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history.id"), index=True)
    library_folder_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library_folder.id"), index=True)
    tool_id: Mapped[Optional[str]] = mapped_column(String(255))
    tool_version: Mapped[Optional[str]] = mapped_column(TEXT, default="1.0.0")
    galaxy_version: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    dynamic_tool_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dynamic_tool.id"), index=True)
    state: Mapped[str] = mapped_column(String(64), index=True, nullable=True)
    info: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    copied_from_job_id: Mapped[Optional[int]]
    command_line: Mapped[Optional[str]] = mapped_column(TEXT)
    dependencies: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    job_messages: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    param_filename: Mapped[Optional[str]] = mapped_column(String(1024))
    runner_name: Mapped[Optional[str]] = mapped_column(String(255))
    job_stdout: Mapped[Optional[str]] = mapped_column(TEXT)
    job_stderr: Mapped[Optional[str]] = mapped_column(TEXT)
    tool_stdout: Mapped[Optional[str]] = mapped_column(TEXT)
    tool_stderr: Mapped[Optional[str]] = mapped_column(TEXT)
    exit_code: Mapped[Optional[int]]
    traceback: Mapped[Optional[str]] = mapped_column(TEXT)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_session.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    job_runner_name: Mapped[Optional[str]] = mapped_column(String(255))
    job_runner_external_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    destination_id: Mapped[Optional[str]] = mapped_column(String(255))
    destination_params: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    object_store_id: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    imported: Mapped[Optional[bool]] = mapped_column(default=False, index=True)
    params: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    handler: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    preferred_object_store_id: Mapped[Optional[str]] = mapped_column(String(255))
    object_store_id_overrides: Mapped[Optional[STR_TO_STR_DICT]] = mapped_column(JSONType)
    tool_request_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tool_request.id"), index=True)

    tool_request: Mapped[Optional["ToolRequest"]] = relationship()
    user: Mapped[Optional["User"]] = relationship()
    galaxy_session: Mapped[Optional["GalaxySession"]] = relationship()
    history: Mapped[Optional["History"]] = relationship(back_populates="jobs")
    library_folder: Mapped[Optional["LibraryFolder"]] = relationship()
    parameters = relationship("JobParameter")
    input_datasets: Mapped[List["JobToInputDatasetAssociation"]] = relationship(
        "JobToInputDatasetAssociation", back_populates="job"
    )
    input_dataset_collections: Mapped[List["JobToInputDatasetCollectionAssociation"]] = relationship(
        back_populates="job"
    )
    input_dataset_collection_elements: Mapped[List["JobToInputDatasetCollectionElementAssociation"]] = relationship(
        back_populates="job"
    )
    output_dataset_collection_instances: Mapped[List["JobToOutputDatasetCollectionAssociation"]] = relationship(
        back_populates="job"
    )
    output_dataset_collections: Mapped[List["JobToImplicitOutputDatasetCollectionAssociation"]] = relationship(
        back_populates="job"
    )
    post_job_actions: Mapped[List["PostJobActionAssociation"]] = relationship(back_populates="job")
    input_library_datasets: Mapped[List["JobToInputLibraryDatasetAssociation"]] = relationship(back_populates="job")
    output_library_datasets: Mapped[List["JobToOutputLibraryDatasetAssociation"]] = relationship(back_populates="job")
    external_output_metadata: Mapped[List["JobExternalOutputMetadata"]] = relationship(back_populates="job")
    tasks: Mapped[List["Task"]] = relationship(back_populates="job")
    output_datasets: Mapped[List["JobToOutputDatasetAssociation"]] = relationship(back_populates="job")
    state_history: Mapped[List["JobStateHistory"]] = relationship()
    text_metrics: Mapped[List["JobMetricText"]] = relationship()
    numeric_metrics: Mapped[List["JobMetricNumeric"]] = relationship()
    interactivetool_entry_points: Mapped[List["InteractiveToolEntryPoint"]] = relationship(
        back_populates="job", uselist=True
    )
    implicit_collection_jobs_association: Mapped[List["ImplicitCollectionJobsJobAssociation"]] = relationship(
        back_populates="job", uselist=False
    )
    container: Mapped[Optional["JobContainerAssociation"]] = relationship(back_populates="job", uselist=False)
    data_manager_association: Mapped[Optional["DataManagerJobAssociation"]] = relationship(
        back_populates="job", uselist=False
    )
    history_dataset_collection_associations: Mapped[List["HistoryDatasetCollectionAssociation"]] = relationship(
        back_populates="job"
    )
    workflow_invocation_step: Mapped[Optional["WorkflowInvocationStep"]] = relationship(
        back_populates="job", uselist=False
    )

    any_output_dataset_collection_instances_deleted = None
    any_output_dataset_deleted = None

    dict_collection_visible_keys = ["id", "state", "exit_code", "update_time", "create_time", "galaxy_version"]
    dict_element_visible_keys = [
        "id",
        "state",
        "exit_code",
        "update_time",
        "create_time",
        "galaxy_version",
        "command_version",
        "copied_from_job_id",
        "user_id",
    ]

    _numeric_metric = JobMetricNumeric
    _text_metric = JobMetricText

    states: TypeAlias = JobState

    # states that are not expected to change, except through admin action or re-scheduling
    terminal_states = [states.OK, states.ERROR, states.DELETED]
    # deleting state should not turn back into any of the non-ready states
    finished_states = terminal_states + [states.DELETING]
    #: job states where the job hasn't finished and the model may still change
    non_ready_states = [
        states.NEW,
        states.RESUBMITTED,
        states.UPLOAD,
        states.WAITING,
        states.QUEUED,
        states.RUNNING,
    ]

    # Please include an accessor (get/set pair) for any new columns/members.
    def __init__(self):
        self.dependencies = []
        self.state = Job.states.NEW
        self.imported = False
        self._init_metrics()
        self.state_history.append(JobStateHistory(self))

    @property
    def running(self):
        return self.state == Job.states.RUNNING

    @property
    def finished(self):
        return self.state in self.finished_states

    def io_dicts(self, exclude_implicit_outputs=False) -> IoDicts:
        inp_data: Dict[str, Optional[DatasetInstance]] = {da.name: da.dataset for da in self.input_datasets}
        out_data: Dict[str, DatasetInstance] = {da.name: da.dataset for da in self.output_datasets}
        inp_data.update([(da.name, da.dataset) for da in self.input_library_datasets])
        out_data.update([(da.name, da.dataset) for da in self.output_library_datasets])

        out_collections: Dict[str, Union[DatasetCollectionInstance, DatasetCollection]]
        if not exclude_implicit_outputs:
            out_collections = {
                obj.name: obj.dataset_collection_instance for obj in self.output_dataset_collection_instances
            }
        else:
            out_collections = {}
            for obj in self.output_dataset_collection_instances:
                if obj.name not in out_data:
                    out_collections[obj.name] = obj.dataset_collection_instance
                # else this is a mapped over output
        out_collections.update([(obj.name, obj.dataset_collection) for obj in self.output_dataset_collections])
        return IoDicts(inp_data, out_data, out_collections)

    # TODO: Add accessors for members defined in SQL Alchemy for the Job table and
    # for the mapper defined to the Job table.
    def get_external_output_metadata(self):
        """
        The external_output_metadata is currently a reference from Job to
        JobExternalOutputMetadata. It exists for a job but not a task.
        """
        return self.external_output_metadata

    def get_session_id(self):
        return self.session_id

    def get_user_id(self):
        return self.user_id

    def get_tool_id(self):
        return self.tool_id

    def get_tool_version(self):
        return self.tool_version

    def get_command_line(self):
        return self.command_line

    def get_dependencies(self):
        return self.dependencies

    def get_param_filename(self):
        return self.param_filename

    def get_parameters(self):
        return self.parameters

    def get_copied_from_job_id(self):
        return self.copied_from_job_id

    def get_input_datasets(self):
        return self.input_datasets

    def get_output_datasets(self):
        return self.output_datasets

    def get_input_library_datasets(self):
        return self.input_library_datasets

    def get_output_library_datasets(self):
        return self.output_library_datasets

    def get_state(self):
        return self.state

    def get_info(self):
        return self.info

    def get_job_runner_name(self):
        # This differs from the Task class in that job_runner_name is
        # accessed instead of task_runner_name. Note that the field
        # runner_name is not the same thing.
        return self.job_runner_name

    def get_job_runner_external_id(self):
        # This is different from the Task just in the member accessed:
        return self.job_runner_external_id

    def get_post_job_actions(self):
        return self.post_job_actions

    def get_imported(self):
        return self.imported

    def get_handler(self):
        return self.handler

    def get_params(self):
        return self.params

    def get_user(self):
        # This is defined in the SQL Alchemy mapper as a relation to the User.
        return self.user

    def get_tasks(self):
        # The tasks member is pert of a reference in the SQL Alchemy schema:
        return self.tasks

    def get_id_tag(self):
        """
        Return a tag that can be useful in identifying a Job.
        This returns the Job's get_id
        """
        return f"{self.id}"

    def set_session_id(self, session_id):
        self.session_id = session_id

    def set_user_id(self, user_id):
        self.user_id = user_id

    def set_tool_id(self, tool_id):
        self.tool_id = tool_id

    def get_user_email(self):
        if self.user is not None:
            return self.user.email
        elif self.galaxy_session is not None and self.galaxy_session.user is not None:
            return self.galaxy_session.user.email
        elif self.history is not None and self.history.user is not None:
            return self.history.user.email
        return None

    def set_tool_version(self, tool_version):
        self.tool_version = tool_version

    def set_command_line(self, command_line):
        self.command_line = command_line

    def set_dependencies(self, dependencies):
        self.dependencies = dependencies

    def set_param_filename(self, param_filename):
        self.param_filename = param_filename

    def set_parameters(self, parameters):
        self.parameters = parameters

    def set_copied_from_job_id(self, job_id):
        self.copied_from_job_id = job_id

    def set_input_datasets(self, input_datasets):
        self.input_datasets = input_datasets

    def set_output_datasets(self, output_datasets):
        self.output_datasets = output_datasets

    def set_input_library_datasets(self, input_library_datasets):
        self.input_library_datasets = input_library_datasets

    def set_output_library_datasets(self, output_library_datasets):
        self.output_library_datasets = output_library_datasets

    def set_info(self, info):
        self.info = info

    def set_runner_name(self, job_runner_name):
        self.job_runner_name = job_runner_name

    def get_job(self):
        # Added so job and task have same interface (.get_job() ) to get at
        # underlying job object.
        return self

    def set_runner_external_id(self, job_runner_external_id):
        self.job_runner_external_id = job_runner_external_id

    def set_post_job_actions(self, post_job_actions):
        self.post_job_actions = post_job_actions

    def set_imported(self, imported):
        self.imported = imported

    def set_handler(self, handler):
        self.handler = handler

    def set_params(self, params):
        self.params = params

    def add_parameter(self, name, value):
        self.parameters.append(JobParameter(name, value))

    def add_input_dataset(self, name, dataset=None, dataset_id=None):
        assoc = JobToInputDatasetAssociation(name, dataset)
        if dataset is None and dataset_id is not None:
            assoc.dataset_id = dataset_id
        add_object_to_object_session(self, assoc)
        self.input_datasets.append(assoc)

    def add_output_dataset(self, name, dataset):
        joda = JobToOutputDatasetAssociation(name, dataset)
        if dataset.dataset.job is None:
            # Only set job if dataset doesn't already have associated job.
            # database operation tools that make copies should not modify the job here.
            dataset.dataset.job = self
        add_object_to_object_session(self, joda)
        self.output_datasets.append(joda)

    def add_input_dataset_collection(self, name, dataset_collection):
        self.input_dataset_collections.append(JobToInputDatasetCollectionAssociation(name, dataset_collection))

    def add_input_dataset_collection_element(self, name, dataset_collection_element):
        self.input_dataset_collection_elements.append(
            JobToInputDatasetCollectionElementAssociation(name, dataset_collection_element)
        )

    def add_output_dataset_collection(self, name, dataset_collection_instance):
        self.output_dataset_collection_instances.append(
            JobToOutputDatasetCollectionAssociation(name, dataset_collection_instance)
        )

    def add_implicit_output_dataset_collection(self, name, dataset_collection):
        self.output_dataset_collections.append(
            JobToImplicitOutputDatasetCollectionAssociation(name, dataset_collection)
        )

    def add_input_library_dataset(self, name, dataset):
        self.input_library_datasets.append(JobToInputLibraryDatasetAssociation(name, dataset))

    def add_output_library_dataset(self, name, dataset):
        self.output_library_datasets.append(JobToOutputLibraryDatasetAssociation(name, dataset))

    def add_post_job_action(self, pja):
        self.post_job_actions.append(PostJobActionAssociation(pja, self))

    def get_change_datatype_actions(self):
        return {
            pja.post_job_action.output_name: pja.post_job_action.action_arguments["newtype"]
            for pja in self.post_job_actions
            if pja.post_job_action.action_type == "ChangeDatatypeAction"
        }

    @property
    def all_entry_points_configured(self):
        # consider an actual DB attribute for this.
        all_configured = True
        for ep in self.interactivetool_entry_points:
            all_configured = ep.configured and all_configured
        return all_configured

    def set_state(self, state: JobState) -> bool:
        """
        Save state history. Returns True if state has changed, else False.
        """
        if self.state == state:
            # Nothing changed, no action needed
            return False
        session = object_session(self)
        if session and self.id and state not in Job.finished_states:
            # Do not update if job is in a terminal state
            rval = session.execute(
                update(Job).where(Job.id == self.id, ~Job.state.in_((state, *Job.finished_states))).values(state=state)
            )
            if rval.rowcount == 1:
                # Need to expire state since we just updated it, but ORM doesn't know about it.
                session.expire(self, ["state"])
                self.state_history.append(JobStateHistory(self))
                return True
            else:
                return False
        else:
            self.state = state
            self.state_history.append(JobStateHistory(self))
            return True

    def get_param_values(self, app, ignore_errors=False):
        """
        Read encoded parameter values from the database and turn back into a
        dict of tool parameter values.
        """
        param_dict = self.raw_param_dict()
        tool = app.toolbox.get_tool(self.tool_id, tool_version=self.tool_version)
        param_dict = tool.params_from_strings(param_dict, app, ignore_errors=ignore_errors)
        return param_dict

    def raw_param_dict(self):
        param_dict = {p.name: p.value for p in self.parameters}
        return param_dict

    def check_if_output_datasets_deleted(self):
        """
        Return true if all of the output datasets associated with this job are
        in the deleted state
        """
        for dataset_assoc in self.output_datasets:
            dataset = dataset_assoc.dataset
            # only the originator of the job can delete a dataset to cause
            # cancellation of the job, no need to loop through history_associations
            if not dataset.deleted:
                return False
        return True

    def mark_stopped(self, track_jobs_in_database=False):
        """
        Mark this job as stopped
        """
        if self.finished:
            # Do not modify the state/outputs of jobs that are already terminal
            return
        if track_jobs_in_database:
            self.state = Job.states.STOPPING
        else:
            self.state = Job.states.STOPPED

    def mark_deleted(self, track_jobs_in_database=False):
        """
        Mark this job as deleted, and mark any output datasets as discarded.
        """
        if self.finished:
            # Do not modify the state/outputs of jobs that are already terminal
            return
        if track_jobs_in_database:
            self.state = Job.states.DELETING
        else:
            self.state = Job.states.DELETED
        self.info = "Job output deleted by user before job completed."
        for jtoda in self.output_datasets:
            output_hda = jtoda.dataset
            output_hda.deleted = True
            output_hda.state = output_hda.states.DISCARDED
            for shared_hda in output_hda.dataset.history_associations:
                # propagate info across shared datasets
                shared_hda.deleted = True
                shared_hda.blurb = "deleted"
                shared_hda.peek = "Job deleted"
                shared_hda.info = "Job output deleted by user before job completed"

    def mark_failed(self, info="Job execution failed", blurb=None, peek=None):
        """
        Mark this job as failed, and mark any output datasets as errored.
        """
        self.state = self.states.FAILED
        self.info = info
        for jtod in self.output_datasets:
            jtod.dataset.state = jtod.dataset.states.ERROR
            for hda in jtod.dataset.dataset.history_associations:
                hda.state = hda.states.ERROR
                if blurb:
                    hda.blurb = blurb
                if peek:
                    hda.peek = peek
                hda.info = info

    def resume(self, flush=True):
        if self.state == self.states.PAUSED:
            self.set_state(self.states.NEW)
            object_session(self).add(self)
            jobs_to_resume = set()
            for jtod in self.output_datasets:
                jobs_to_resume.update(jtod.dataset.unpause_dependent_jobs(jobs_to_resume))
            for job in jobs_to_resume:
                job.resume(flush=False)
            if flush:
                session = object_session(self)
                with transaction(session):
                    session.commit()

    def _serialize(self, id_encoder, serialization_options):
        job_attrs = dict_for(self)
        serialization_options.attach_identifier(id_encoder, self, job_attrs)
        job_attrs["tool_id"] = self.tool_id
        job_attrs["tool_version"] = self.tool_version
        job_attrs["galaxy_version"] = self.galaxy_version
        job_attrs["state"] = self.state
        job_attrs["info"] = self.info
        job_attrs["traceback"] = self.traceback
        job_attrs["command_line"] = self.command_line
        job_attrs["tool_stderr"] = self.tool_stderr
        job_attrs["job_stderr"] = self.job_stderr
        job_attrs["tool_stdout"] = self.tool_stdout
        job_attrs["job_stdout"] = self.job_stdout
        job_attrs["exit_code"] = self.exit_code
        job_attrs["create_time"] = self.create_time.isoformat()
        job_attrs["update_time"] = self.update_time.isoformat()
        job_attrs["job_messages"] = self.job_messages

        # Get the job's parameters
        param_dict = self.raw_param_dict()
        params_objects = {}
        for key in param_dict:
            params_objects[key] = safe_loads(param_dict[key])

        def remap_objects(p, k, obj):
            if isinstance(obj, dict) and "src" in obj and obj["src"] in ["hda", "hdca", "dce"]:
                new_id = serialization_options.get_identifier_for_id(id_encoder, obj["id"])
                new_obj = obj.copy()
                new_obj["id"] = new_id
                return (k, new_obj)
            return (k, obj)

        params_objects = remap(params_objects, remap_objects)

        params_dict = {}
        for name, value in params_objects.items():
            params_dict[name] = value
        job_attrs["params"] = params_dict
        return job_attrs

    def requires_shareable_storage(self, security_agent):
        # An easy optimization would be to calculate this in galaxy.tools.actions when the
        # job is created and all the output permissions are already known. Having to reload
        # these permissions in the job code shouldn't strictly be needed.

        requires_sharing = False
        for dataset_assoc in self.output_datasets + self.output_library_datasets:
            if not security_agent.dataset_is_private_to_a_user(dataset_assoc.dataset.dataset):
                requires_sharing = True
                break

        return requires_sharing

    def to_dict(self, view="collection", system_details=False):
        if view == "admin_job_list":
            rval = super().to_dict(view="collection")
        else:
            rval = super().to_dict(view=view)
        rval["tool_id"] = self.tool_id
        rval["tool_version"] = self.tool_version
        rval["history_id"] = self.history_id
        if system_details or view == "admin_job_list":
            # System level details that only admins should have.
            rval["external_id"] = self.job_runner_external_id
            rval["command_line"] = self.command_line
            rval["traceback"] = self.traceback
        if view == "admin_job_list":
            rval["user_email"] = self.user.email if self.user else None
            rval["handler"] = self.handler
            rval["job_runner_name"] = self.job_runner_name
            rval["info"] = self.info
            rval["session_id"] = self.session_id
            if self.galaxy_session and self.galaxy_session.remote_host:
                rval["remote_host"] = self.galaxy_session.remote_host
        if view == "element":
            param_dict = {p.name: p.value for p in self.parameters}
            rval["params"] = param_dict

            input_dict = {}
            for i in self.input_datasets:
                if i.dataset is not None:
                    input_dict[i.name] = {
                        "id": i.dataset.id,
                        "src": "hda",
                        "uuid": str(i.dataset.dataset.uuid) if i.dataset.dataset.uuid is not None else None,
                    }
            for i in self.input_library_datasets:
                if i.dataset is not None:
                    input_dict[i.name] = {
                        "id": i.dataset.id,
                        "src": "ldda",
                        "uuid": str(i.dataset.dataset.uuid) if i.dataset.dataset.uuid is not None else None,
                    }
            for k in input_dict:
                if k in param_dict:
                    del param_dict[k]
            rval["inputs"] = input_dict

            output_dict = {}
            for i in self.output_datasets:
                if i.dataset is not None:
                    output_dict[i.name] = {
                        "id": i.dataset.id,
                        "src": "hda",
                        "uuid": str(i.dataset.dataset.uuid) if i.dataset.dataset.uuid is not None else None,
                    }
            for i in self.output_library_datasets:
                if i.dataset is not None:
                    output_dict[i.name] = {
                        "id": i.dataset.id,
                        "src": "ldda",
                        "uuid": str(i.dataset.dataset.uuid) if i.dataset.dataset.uuid is not None else None,
                    }
            rval["outputs"] = output_dict
            rval["output_collections"] = {
                jtodca.name: {"id": jtodca.dataset_collection_instance.id, "src": "hdca"}
                for jtodca in self.output_dataset_collection_instances
            }

        return rval

    def update_hdca_update_time_for_job(self, update_time, sa_session, supports_skip_locked):
        subq = (
            sa_session.query(HistoryDatasetCollectionAssociation.id)
            .join(ImplicitCollectionJobs)
            .join(ImplicitCollectionJobsJobAssociation)
            .filter(ImplicitCollectionJobsJobAssociation.job_id == self.id)
        )
        if supports_skip_locked:
            subq = subq.with_for_update(skip_locked=True).subquery()
        implicit_statement = (
            HistoryDatasetCollectionAssociation.table.update()
            .where(HistoryDatasetCollectionAssociation.id.in_(select(subq)))
            .values(update_time=update_time)
        )
        explicit_statement = (
            HistoryDatasetCollectionAssociation.table.update()
            .where(HistoryDatasetCollectionAssociation.job_id == self.id)
            .values(update_time=update_time)
        )
        sa_session.execute(explicit_statement)
        if supports_skip_locked:
            sa_session.execute(implicit_statement)
        else:
            conn = sa_session.connection(execution_options={"isolation_level": "SERIALIZABLE"})
            with conn.begin() as trans:
                try:
                    conn.execute(implicit_statement)
                    trans.commit()
                except OperationalError as e:
                    # If this is a serialization failure on PostgreSQL, then e.orig is a psycopg2 TransactionRollbackError
                    # and should have attribute `code`. Other engines should just report the message and move on.
                    if int(getattr(e.orig, "pgcode", -1)) != 40001:
                        log.debug(
                            f"Updating implicit collection uptime_time for job {self.id} failed (this is expected for large collections and not a problem): {unicodify(e)}"
                        )
                    trans.rollback()

    def set_final_state(self, final_state, supports_skip_locked):
        self.set_state(final_state)
        # TODO: migrate to where-in subqueries?
        statement = text(
            """
            UPDATE workflow_invocation_step
            SET update_time = :update_time
            WHERE job_id = :job_id;
        """
        )
        sa_session = object_session(self)
        update_time = now()
        self.update_hdca_update_time_for_job(
            update_time=update_time, sa_session=sa_session, supports_skip_locked=supports_skip_locked
        )
        params = {"job_id": self.id, "update_time": update_time}
        sa_session.execute(statement, params)

    def get_destination_configuration(self, dest_params, config, key, default=None):
        """Get a destination parameter that can be defaulted back
        in specified config if it needs to be applied globally.
        """
        param_unspecified = object()
        config_value = (self.destination_params or {}).get(key, param_unspecified)
        if config_value is param_unspecified:
            config_value = dest_params.get(key, param_unspecified)
        if config_value is param_unspecified:
            config_value = getattr(config, key, param_unspecified)
        if config_value is param_unspecified:
            config_value = default
        return config_value

    @property
    def command_version(self):
        # TODO: make actual database property and track properly - we should be recording this on the job and not on the datasets
        for dataset_assoc in self.output_datasets:
            return dataset_assoc.dataset.tool_version

    def update_output_states(self, supports_skip_locked):
        # TODO: migrate to where-in subqueries?
        statements = [
            text(
                """
            UPDATE dataset
            SET
                state = :state,
                update_time = :update_time
            WHERE
                dataset.job_id = :job_id
        """
            ),
            text(
                """
            UPDATE history_dataset_association
            SET
                info = :info,
                update_time = :update_time
            FROM dataset
            WHERE
                history_dataset_association.dataset_id = dataset.id
                AND dataset.job_id = :job_id;
        """
            ),
            text(
                """
            UPDATE library_dataset_dataset_association
            SET
                info = :info,
                update_time = :update_time
            FROM dataset
            WHERE
                library_dataset_dataset_association.dataset_id = dataset.id
                AND dataset.job_id = :job_id;
        """
            ),
        ]
        sa_session = object_session(self)
        update_time = now()
        self.update_hdca_update_time_for_job(
            update_time=update_time, sa_session=sa_session, supports_skip_locked=supports_skip_locked
        )
        params = {"job_id": self.id, "state": self.state, "info": self.info, "update_time": update_time}
        for statement in statements:
            sa_session.execute(statement, params)

    def remappable(self):
        """
        Check whether job is remappable when rerun
        """
        if self.state == self.states.ERROR:
            try:
                for jtod in self.output_datasets:
                    if jtod.dataset.dependent_jobs:
                        return True
                if self.output_dataset_collection_instances:
                    # We'll want to replace this item
                    return "job_produced_collection_elements"
            except Exception:
                log.exception(f"Error trying to determine if job {self.id} is remappable")
        return False

    def hide_outputs(self, flush=True):
        for output_association in self.output_datasets + self.output_dataset_collection_instances:
            output_association.item.visible = False
        if flush:
            session = object_session(self)
            with transaction(session):
                session.commit()


class Task(Base, JobLike, RepresentById):
    """
    A task represents a single component of a job.
    """

    __tablename__ = "task"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    execution_time: Mapped[Optional[datetime]]
    update_time: Mapped[Optional[datetime]] = mapped_column(default=now, onupdate=now)
    state: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    command_line: Mapped[Optional[str]] = mapped_column(TEXT)
    param_filename: Mapped[Optional[str]] = mapped_column(String(1024))
    runner_name: Mapped[Optional[str]] = mapped_column(String(255))
    job_stdout: Mapped[Optional[str]] = mapped_column(
        TEXT
    )  # job_stdout makes sense here because it is short for job script standard out
    job_stderr: Mapped[Optional[str]] = mapped_column(TEXT)
    tool_stdout: Mapped[Optional[str]] = mapped_column(TEXT)
    tool_stderr: Mapped[Optional[str]] = mapped_column(TEXT)
    exit_code: Mapped[Optional[int]]
    job_messages: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    info: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    traceback: Mapped[Optional[str]] = mapped_column(TEXT)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True)
    working_directory: Mapped[Optional[str]] = mapped_column(String(1024))
    task_runner_name: Mapped[Optional[str]] = mapped_column(String(255))
    task_runner_external_id: Mapped[Optional[str]] = mapped_column(String(255))
    prepare_input_files_cmd: Mapped[Optional[str]] = mapped_column(TEXT)
    job: Mapped["Job"] = relationship(back_populates="tasks")
    text_metrics: Mapped[List["TaskMetricText"]] = relationship()
    numeric_metrics: Mapped[List["TaskMetricNumeric"]] = relationship()

    _numeric_metric = TaskMetricNumeric
    _text_metric = TaskMetricText

    class states(str, Enum):
        NEW = "new"
        WAITING = "waiting"
        QUEUED = "queued"
        RUNNING = "running"
        OK = "ok"
        ERROR = "error"
        DELETED = "deleted"

    # Please include an accessor (get/set pair) for any new columns/members.
    def __init__(self, job, working_directory, prepare_files_cmd):
        self.parameters = []
        self.state = Task.states.NEW
        self.working_directory = working_directory
        add_object_to_object_session(self, job)
        self.job = job
        self.prepare_input_files_cmd = prepare_files_cmd
        self._init_metrics()

    def get_param_values(self, app):
        """
        Read encoded parameter values from the database and turn back into a
        dict of tool parameter values.
        """
        param_dict = {p.name: p.value for p in self.job.parameters}
        tool = app.toolbox.get_tool(self.job.tool_id, tool_version=self.job.tool_version)
        param_dict = tool.params_from_strings(param_dict, app)
        return param_dict

    def get_id_tag(self):
        """
        Return an id tag suitable for identifying the task.
        This combines the task's job id and the task's own id.
        """
        return f"{self.job.id}_{self.id}"

    def get_command_line(self):
        return self.command_line

    def get_parameters(self):
        return self.parameters

    def get_state(self):
        return self.state

    def get_info(self):
        return self.info

    def get_working_directory(self):
        return self.working_directory

    def get_task_runner_name(self):
        return self.task_runner_name

    def get_task_runner_external_id(self):
        return self.task_runner_external_id

    def get_job(self):
        return self.job

    def get_prepare_input_files_cmd(self):
        return self.prepare_input_files_cmd

    # The following accessors are for members that are in the Job class but
    # not in the Task class. So they can either refer to the parent Job
    # or return None, depending on whether Tasks need to point to the parent
    # (e.g., for a session) or never use the member (e.g., external output
    # metdata). These can be filled in as needed.
    def get_external_output_metadata(self):
        """
        The external_output_metadata is currently a backref to
        JobExternalOutputMetadata. It exists for a job but not a task,
        and when a task is cancelled its corresponding parent Job will
        be cancelled. So None is returned now, but that could be changed
        to self.get_job().get_external_output_metadata().
        """
        return None

    def get_job_runner_name(self):
        """
        Since runners currently access Tasks the same way they access Jobs,
        this method just refers to *this* instance's runner.
        """
        return self.task_runner_name

    def get_job_runner_external_id(self):
        """
        Runners will use the same methods to get information about the Task
        class as they will about the Job class, so this method just returns
        the task's external id.
        """
        # TODO: Merge into get_runner_external_id.
        return self.task_runner_external_id

    def get_session_id(self):
        # The Job's galaxy session is equal to the Job's session, so the
        # Job's session is the same as the Task's session.
        return self.get_job().get_session_id()

    def set_id(self, id):
        # This is defined in the SQL Alchemy's mapper and not here.
        # This should never be called.
        self.id = id

    def set_command_line(self, command_line):
        self.command_line = command_line

    def set_parameters(self, parameters):
        self.parameters = parameters

    def set_state(self, state):
        self.state = state

    def set_info(self, info):
        self.info = info

    def set_working_directory(self, working_directory):
        self.working_directory = working_directory

    def set_task_runner_name(self, task_runner_name):
        self.task_runner_name = task_runner_name

    def set_job_runner_external_id(self, task_runner_external_id):
        # This method is available for runners that do not want/need to
        # differentiate between the kinds of Runnable things (Jobs and Tasks)
        # that they're using.
        log.debug("Task %d: Set external id to %s", self.id, task_runner_external_id)
        self.task_runner_external_id = task_runner_external_id

    def set_task_runner_external_id(self, task_runner_external_id):
        self.task_runner_external_id = task_runner_external_id

    def set_job(self, job):
        self.job = job

    def set_prepare_input_files_cmd(self, prepare_input_files_cmd):
        self.prepare_input_files_cmd = prepare_input_files_cmd


class JobParameter(Base, RepresentById):
    __tablename__ = "job_parameter"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    value: Mapped[Optional[str]] = mapped_column(TEXT)

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def copy(self):
        return JobParameter(name=self.name, value=self.value)


class JobToInputDatasetAssociation(Base, RepresentById):
    __tablename__ = "job_to_input_dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True, nullable=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("history_dataset_association.id"), index=True, nullable=True)
    dataset_version: Mapped[Optional[int]]
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    dataset: Mapped["HistoryDatasetAssociation"] = relationship(lazy="joined", back_populates="dependent_jobs")
    job: Mapped["Job"] = relationship(back_populates="input_datasets")

    def __init__(self, name, dataset):
        self.name = name
        add_object_to_object_session(self, dataset)
        self.dataset = dataset
        self.dataset_version = 0  # We start with version 0 and update once the job is ready


class JobToOutputDatasetAssociation(Base, RepresentById):
    __tablename__ = "job_to_output_dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True, nullable=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("history_dataset_association.id"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    dataset: Mapped["HistoryDatasetAssociation"] = relationship(
        lazy="joined", back_populates="creating_job_associations"
    )
    job: Mapped["Job"] = relationship(back_populates="output_datasets")

    def __init__(self, name, dataset):
        self.name = name
        add_object_to_object_session(self, dataset)
        self.dataset = dataset

    @property
    def item(self):
        return self.dataset


class JobToInputDatasetCollectionAssociation(Base, RepresentById):
    __tablename__ = "job_to_input_dataset_collection"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True, nullable=True)
    dataset_collection_id: Mapped[int] = mapped_column(
        ForeignKey("history_dataset_collection_association.id"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    dataset_collection: Mapped["HistoryDatasetCollectionAssociation"] = relationship(lazy="joined")
    job: Mapped["Job"] = relationship(back_populates="input_dataset_collections")

    def __init__(self, name, dataset_collection):
        self.name = name
        self.dataset_collection = dataset_collection


class JobToInputDatasetCollectionElementAssociation(Base, RepresentById):
    __tablename__ = "job_to_input_dataset_collection_element"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True, nullable=True)
    dataset_collection_element_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_collection_element.id"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(Unicode(255), nullable=True)
    dataset_collection_element: Mapped["DatasetCollectionElement"] = relationship(lazy="joined")
    job: Mapped["Job"] = relationship(back_populates="input_dataset_collection_elements")

    def __init__(self, name, dataset_collection_element):
        self.name = name
        self.dataset_collection_element = dataset_collection_element


# Many jobs may map to one HistoryDatasetCollection using these for a given
# tool output (if mapping over an input collection).
class JobToOutputDatasetCollectionAssociation(Base, RepresentById):
    __tablename__ = "job_to_output_dataset_collection"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True, nullable=True)
    dataset_collection_id: Mapped[int] = mapped_column(
        ForeignKey("history_dataset_collection_association.id"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(Unicode(255), nullable=True)
    dataset_collection_instance: Mapped["HistoryDatasetCollectionAssociation"] = relationship(lazy="joined")
    job: Mapped["Job"] = relationship(back_populates="output_dataset_collection_instances")

    def __init__(self, name, dataset_collection_instance):
        self.name = name
        self.dataset_collection_instance = dataset_collection_instance

    @property
    def item(self):
        return self.dataset_collection_instance


# A DatasetCollection will be mapped to at most one job per tool output
# using these. (You can think of many of these models as going into the
# creation of a JobToOutputDatasetCollectionAssociation.)
class JobToImplicitOutputDatasetCollectionAssociation(Base, RepresentById):
    __tablename__ = "job_to_implicit_output_dataset_collection"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True, nullable=True)
    dataset_collection_id: Mapped[int] = mapped_column(ForeignKey("dataset_collection.id"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(Unicode(255), nullable=True)
    dataset_collection: Mapped["DatasetCollection"] = relationship()
    job: Mapped["Job"] = relationship(back_populates="output_dataset_collections")

    def __init__(self, name, dataset_collection):
        self.name = name
        self.dataset_collection = dataset_collection


class JobToInputLibraryDatasetAssociation(Base, RepresentById):
    __tablename__ = "job_to_input_library_dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True, nullable=True)
    ldda_id: Mapped[int] = mapped_column(
        ForeignKey("library_dataset_dataset_association.id"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(Unicode(255), nullable=True)
    job: Mapped["Job"] = relationship(back_populates="input_library_datasets")
    dataset: Mapped["LibraryDatasetDatasetAssociation"] = relationship(lazy="joined", back_populates="dependent_jobs")

    def __init__(self, name, dataset):
        self.name = name
        add_object_to_object_session(self, dataset)
        self.dataset = dataset


class JobToOutputLibraryDatasetAssociation(Base, RepresentById):
    __tablename__ = "job_to_output_library_dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True, nullable=True)
    ldda_id: Mapped[int] = mapped_column(
        ForeignKey("library_dataset_dataset_association.id"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(Unicode(255), nullable=True)
    job: Mapped["Job"] = relationship(back_populates="output_library_datasets")
    dataset: Mapped["LibraryDatasetDatasetAssociation"] = relationship(
        lazy="joined", back_populates="creating_job_associations"
    )

    def __init__(self, name, dataset):
        self.name = name
        add_object_to_object_session(self, dataset)
        self.dataset = dataset


class JobStateHistory(Base, RepresentById):
    __tablename__ = "job_state_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    state: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    info: Mapped[Optional[str]] = mapped_column(TrimmedString(255))

    def __init__(self, job):
        self.job_id = job.id
        self.state = job.state
        self.info = job.info


class ImplicitlyCreatedDatasetCollectionInput(Base, RepresentById):
    __tablename__ = "implicitly_created_dataset_collection_inputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_collection_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("history_dataset_collection_association.id"), index=True
    )
    input_dataset_collection_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("history_dataset_collection_association.id"), index=True
    )
    name: Mapped[Optional[str]] = mapped_column(Unicode(255))

    input_dataset_collection: Mapped[Optional["HistoryDatasetCollectionAssociation"]] = relationship(
        primaryjoin=(
            lambda: HistoryDatasetCollectionAssociation.id
            == ImplicitlyCreatedDatasetCollectionInput.input_dataset_collection_id
        ),
    )

    def __init__(self, name, input_dataset_collection):
        self.name = name
        self.input_dataset_collection = input_dataset_collection


class ImplicitCollectionJobs(Base, Serializable):
    __tablename__ = "implicit_collection_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    populated_state: Mapped[str] = mapped_column(TrimmedString(64), default="new")
    jobs: Mapped[List["ImplicitCollectionJobsJobAssociation"]] = relationship(back_populates="implicit_collection_jobs")

    class populated_states(str, Enum):
        NEW = "new"  # New implicit jobs object, unpopulated job associations
        OK = "ok"  # Job associations are set and fixed.
        FAILED = "failed"  # There were issues populating job associations, object is in error.

    def __init__(self, populated_state=None):
        self.populated_state = populated_state or ImplicitCollectionJobs.populated_states.NEW

    @property
    def job_list(self):
        return [icjja.job for icjja in self.jobs]

    def _serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            populated_state=self.populated_state,
            jobs=[serialization_options.get_identifier(id_encoder, j_a.job) for j_a in self.jobs],
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval


class ImplicitCollectionJobsJobAssociation(Base, RepresentById):
    __tablename__ = "implicit_collection_jobs_job_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    implicit_collection_jobs_id: Mapped[int] = mapped_column(
        ForeignKey("implicit_collection_jobs.id"), index=True, nullable=True
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job.id"), index=True, nullable=True
    )  # Consider making this nullable...
    order_index: Mapped[int]
    implicit_collection_jobs = relationship("ImplicitCollectionJobs", back_populates="jobs")
    job: Mapped["Job"] = relationship(back_populates="implicit_collection_jobs_association")


class PostJobAction(Base, RepresentById):
    __tablename__ = "post_job_action"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(255))
    output_name: Mapped[Optional[str]] = mapped_column(String(255))
    _action_arguments: Mapped[Optional[Dict[str, Any]]] = mapped_column("action_arguments", MutableJSONType)
    workflow_step: Mapped[Optional["WorkflowStep"]] = relationship(
        back_populates="post_job_actions",
        primaryjoin=(lambda: WorkflowStep.id == PostJobAction.workflow_step_id),
    )

    def __init__(self, action_type, workflow_step=None, output_name=None, action_arguments=None):
        self.action_type = action_type
        self.output_name = output_name
        self.action_arguments = action_arguments
        self.workflow_step = workflow_step
        ensure_object_added_to_session(self, object_in_session=workflow_step)

    @property
    def action_arguments(self):
        if self.action_type in ("HideDatasetAction", "DeleteIntermediatesAction") and self._action_arguments is True:
            # Fix up broken workflows resulting from imports with gxformat2 <= 0.20.0
            return {}
        else:
            return self._action_arguments

    @action_arguments.setter
    def action_arguments(self, value: Dict[str, Any]):
        self._action_arguments = value


class PostJobActionAssociation(Base, RepresentById):
    __tablename__ = "post_job_action_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True)
    post_job_action_id: Mapped[int] = mapped_column(ForeignKey("post_job_action.id"), index=True)
    post_job_action: Mapped["PostJobAction"] = relationship()
    job: Mapped["Job"] = relationship(back_populates="post_job_actions")

    def __init__(self, pja, job=None, job_id=None):
        if job is not None:
            self.job = job
            ensure_object_added_to_session(self, object_in_session=job)
        elif job_id is not None:
            self.job_id = job_id
        else:
            raise Exception("PostJobActionAssociation must be created with a job or a job_id.")
        self.post_job_action = pja


class JobExternalOutputMetadata(Base, RepresentById):
    __tablename__ = "job_external_output_metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    history_dataset_association_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("history_dataset_association.id"), index=True
    )
    library_dataset_dataset_association_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("library_dataset_dataset_association.id"), index=True
    )
    is_valid: Mapped[Optional[bool]] = mapped_column(default=True)
    filename_in: Mapped[Optional[str]] = mapped_column(String(255))
    filename_out: Mapped[Optional[str]] = mapped_column(String(255))
    filename_results_code: Mapped[Optional[str]] = mapped_column(String(255))
    filename_kwds: Mapped[Optional[str]] = mapped_column(String(255))
    filename_override_metadata: Mapped[Optional[str]] = mapped_column(String(255))
    job_runner_external_pid: Mapped[Optional[str]] = mapped_column(String(255))
    history_dataset_association: Mapped[Optional["HistoryDatasetAssociation"]] = relationship(lazy="joined")
    library_dataset_dataset_association: Mapped[Optional["LibraryDatasetDatasetAssociation"]] = relationship(
        lazy="joined"
    )
    job: Mapped[Optional["Job"]] = relationship(back_populates="external_output_metadata")

    def __init__(self, job=None, dataset=None):
        add_object_to_object_session(self, job)
        self.job = job
        if isinstance(dataset, galaxy.model.HistoryDatasetAssociation):
            self.history_dataset_association = dataset
        elif isinstance(dataset, galaxy.model.LibraryDatasetDatasetAssociation):
            self.library_dataset_dataset_association = dataset

    @property
    def dataset(self):
        if self.history_dataset_association:
            return self.history_dataset_association
        elif self.library_dataset_dataset_association:
            return self.library_dataset_dataset_association
        return None


# Set up output dataset association for export history jobs. Because job
# uses a Dataset rather than an HDA or LDA, it's necessary to set up a
# fake dataset association that provides the needed attributes for
# preparing a job.
class FakeDatasetAssociation:
    fake_dataset_association = True

    def __init__(self, dataset: Optional["Dataset"] = None) -> None:
        self.dataset = dataset
        self.metadata: Dict = {}
        self.has_deferred_data = False

    def get_file_name(self, sync_cache: bool = True) -> str:
        assert self.dataset
        return self.dataset.get_file_name(sync_cache)

    def __eq__(self, other):
        return isinstance(other, FakeDatasetAssociation) and self.dataset == other.dataset


class JobExportHistoryArchive(Base, RepresentById):
    __tablename__ = "job_export_history_archive"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    history_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history.id"), index=True)
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dataset.id"), index=True)
    compressed: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    history_attrs_filename: Mapped[Optional[str]] = mapped_column(TEXT)
    job: Mapped[Optional["Job"]] = relationship()
    dataset: Mapped[Optional["Dataset"]] = relationship()
    history: Mapped[Optional["History"]] = relationship(back_populates="exports")

    ATTRS_FILENAME_HISTORY = "history_attrs.txt"

    def __init__(self, compressed=False, **kwd):
        if "history" in kwd:
            add_object_to_object_session(self, kwd["history"])
        super().__init__(**kwd)
        self.compressed = compressed

    @property
    def fda(self):
        return FakeDatasetAssociation(self.dataset)

    @property
    def temp_directory(self):
        return os.path.split(self.history_attrs_filename)[0]

    @property
    def up_to_date(self):
        """Return False, if a new export should be generated for corresponding
        history.
        """
        job = self.job
        return job.state not in [Job.states.ERROR, Job.states.DELETED] and job.update_time > self.history.update_time

    @property
    def ready(self):
        return self.job.state == Job.states.OK

    @property
    def preparing(self):
        return self.job.state in [Job.states.RUNNING, Job.states.QUEUED, Job.states.WAITING]

    @property
    def export_name(self):
        # Stream archive.
        hname = ready_name_for_url(self.history.name)
        hname = f"Galaxy-History-{hname}.tar"
        if self.compressed:
            hname += ".gz"
        return hname

    @staticmethod
    def create_for_history(history, job, sa_session, object_store, compressed):
        # Create dataset that will serve as archive.
        archive_dataset = Dataset()
        sa_session.add(archive_dataset)

        with transaction(sa_session):
            sa_session.commit()  # ensure job.id and archive_dataset.id are available

        object_store.create(archive_dataset)  # set the object store id, create dataset (if applicable)
        # Add association for keeping track of job, history, archive relationship.
        jeha = JobExportHistoryArchive(job=job, history=history, dataset=archive_dataset, compressed=compressed)
        sa_session.add(jeha)

        #
        # Create attributes/metadata files for export.
        #
        jeha.dataset.create_extra_files_path()
        temp_output_dir = jeha.dataset.extra_files_path

        history_attrs_filename = os.path.join(temp_output_dir, jeha.ATTRS_FILENAME_HISTORY)
        jeha.history_attrs_filename = history_attrs_filename
        return jeha

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job.id,
            "ready": self.ready,
            "preparing": self.preparing,
            "up_to_date": self.up_to_date,
        }


class JobImportHistoryArchive(Base, RepresentById):
    __tablename__ = "job_import_history_archive"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    history_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history.id"), index=True)
    archive_dir: Mapped[Optional[str]] = mapped_column(TEXT)
    job: Mapped[Optional["Job"]] = relationship()
    history: Mapped[Optional["History"]] = relationship()


class StoreExportAssociation(Base, RepresentById):
    __tablename__ = "store_export_association"
    __table_args__ = (Index("ix_store_export_object", "object_id", "object_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_uuid: Mapped[Optional[Union[UUID, str]]] = mapped_column(UUIDType(), index=True, unique=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    object_type: Mapped[Optional[str]] = mapped_column(TrimmedString(32))
    object_id: Mapped[Optional[int]]
    export_metadata: Mapped[Optional[bytes]] = mapped_column(JSONType)


class JobContainerAssociation(Base, RepresentById):
    __tablename__ = "job_container_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), index=True, nullable=True)
    container_type: Mapped[Optional[str]] = mapped_column(TEXT)
    container_name: Mapped[Optional[str]] = mapped_column(TEXT)
    container_info: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    created_time: Mapped[Optional[datetime]] = mapped_column(default=now)
    modified_time: Mapped[Optional[datetime]] = mapped_column(default=now, onupdate=now)
    job: Mapped["Job"] = relationship(back_populates="container")

    def __init__(self, **kwd):
        if "job" in kwd:
            add_object_to_object_session(self, kwd["job"])
        super().__init__(**kwd)
        self.container_info = self.container_info or {}


class InteractiveToolEntryPoint(Base, Dictifiable, RepresentById):
    __tablename__ = "interactivetool_entry_point"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    name: Mapped[Optional[str]] = mapped_column(TEXT)
    token: Mapped[Optional[str]] = mapped_column(TEXT)
    tool_port: Mapped[Optional[int]]
    host: Mapped[Optional[str]] = mapped_column(TEXT)
    port: Mapped[Optional[int]]
    protocol: Mapped[Optional[str]] = mapped_column(TEXT)
    entry_url: Mapped[Optional[str]] = mapped_column(TEXT)
    requires_domain: Mapped[Optional[bool]] = mapped_column(default=True)
    requires_path_in_url: Mapped[Optional[bool]] = mapped_column(default=False)
    requires_path_in_header_named: Mapped[Optional[str]] = mapped_column(TEXT)
    info: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    configured: Mapped[Optional[bool]] = mapped_column(default=False)
    deleted: Mapped[Optional[bool]] = mapped_column(default=False)
    created_time: Mapped[Optional[datetime]] = mapped_column(default=now)
    modified_time: Mapped[Optional[datetime]] = mapped_column(default=now, onupdate=now)
    label: Mapped[Optional[str]] = mapped_column(TEXT)
    job: Mapped[Optional["Job"]] = relationship(back_populates="interactivetool_entry_points", uselist=False)

    dict_collection_visible_keys = [
        "id",
        "job_id",
        "name",
        "label",
        "active",
        "created_time",
        "modified_time",
        "output_datasets_ids",
    ]
    dict_element_visible_keys = [
        "id",
        "job_id",
        "name",
        "label",
        "active",
        "created_time",
        "modified_time",
        "output_datasets_ids",
    ]

    def __init__(
        self,
        requires_domain=True,
        requires_path_in_url=False,
        configured=False,
        deleted=False,
        **kwd,
    ):
        super().__init__(**kwd)
        self.requires_domain = requires_domain
        self.requires_path_in_url = requires_path_in_url
        self.configured = configured
        self.deleted = deleted
        self.token = self.token or hex_to_lowercase_alphanum(token_hex(8))
        self.info = self.info or {}

    @property
    def active(self):
        if self.configured and not self.deleted:
            return self.job.running
        return False

    @property
    def class_id(self):
        return "ep"

    @property
    def output_datasets_ids(self):
        return [da.dataset.id for da in self.job.output_datasets]


class GenomeIndexToolData(Base, RepresentById):  # TODO: params arg is lost
    __tablename__ = "genome_index_tool_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dataset.id"), index=True)
    fasta_path: Mapped[Optional[str]] = mapped_column(String(255))
    created_time: Mapped[Optional[datetime]] = mapped_column(default=now)
    modified_time: Mapped[Optional[datetime]] = mapped_column(default=now, onupdate=now)
    indexer: Mapped[Optional[str]] = mapped_column(String(64))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    job: Mapped[Optional["Job"]] = relationship()
    dataset: Mapped[Optional["Dataset"]] = relationship()
    user: Mapped[Optional["User"]] = relationship()


class ChatExchange(Base, RepresentById):

    __tablename__ = "chat_exchange"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), index=True, nullable=False)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True, nullable=True)

    user: Mapped["User"] = relationship(back_populates="chat_exchanges")
    messages: Mapped[List["ChatExchangeMessage"]] = relationship(back_populates="chat_exchange")

    def __init__(self, user, job_id=None, message=None, **kwargs):
        self.user = user
        self.job_id = job_id
        self.messages = []
        if message:
            self.add_message(message)

    def add_message(self, message):
        self.messages.append(ChatExchangeMessage(message=message))


class ChatExchangeMessage(Base, RepresentById):
    __tablename__ = "chat_exchange_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_exchange_id: Mapped[int] = mapped_column(ForeignKey("chat_exchange.id"), index=True)
    create_time: Mapped[datetime] = mapped_column(default=now)
    message: Mapped[str] = mapped_column(Text)
    feedback: Mapped[Optional[int]] = mapped_column(Integer)
    chat_exchange: Mapped["ChatExchange"] = relationship("ChatExchange", back_populates="messages")

    def __init__(self, message, feedback=None):
        self.message = message
        self.feedback = feedback


class Group(Base, Dictifiable, RepresentById):
    __tablename__ = "galaxy_group"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), index=True, unique=True)
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    quotas: Mapped[List["GroupQuotaAssociation"]] = relationship(back_populates="group")
    roles: Mapped[List["GroupRoleAssociation"]] = relationship(back_populates="group")
    users: Mapped[List["UserGroupAssociation"]] = relationship("UserGroupAssociation", back_populates="group")

    dict_collection_visible_keys = ["id", "name"]
    dict_element_visible_keys = ["id", "name"]

    def __init__(self, name=None):
        self.name = name
        self.deleted = False


class UserGroupAssociation(Base, RepresentById):
    __tablename__ = "user_group_association"
    __table_args__ = (UniqueConstraint("user_id", "group_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("galaxy_group.id"), index=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    user: Mapped["User"] = relationship(back_populates="groups")
    group: Mapped["Group"] = relationship(back_populates="users")

    def __init__(self, user, group):
        add_object_to_object_session(self, user)
        self.user = user
        self.group = group


class Notification(Base, Dictifiable, RepresentById):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    publication_time: Mapped[Optional[datetime]] = mapped_column(
        default=now
    )  # The date of publication, can be a future date to allow scheduling
    expiration_time: Mapped[Optional[datetime]] = mapped_column(
        default=now() + timedelta(days=30 * 6)
    )  # The expiration date, expired notifications will be permanently removed from DB regularly
    source: Mapped[str] = mapped_column(
        String(32), index=True, nullable=True
    )  # Who (or what) generated the notification
    category: Mapped[str] = mapped_column(
        String(64), index=True, nullable=True
    )  # Category of the notification, defines its contents. Used for filtering, un/subscribing, etc
    variant: Mapped[str] = mapped_column(
        String(16), index=True, nullable=True
    )  # Defines the 'importance' of the notification ('info', 'warning', 'urgent', etc.). Used for filtering, highlight rendering, etc
    dispatched: Mapped[bool] = mapped_column(
        Boolean, index=True, default=False
    )  # Whether the notification has been dispatched to users via other channels
    galaxy_url: Mapped[Optional[str]] = mapped_column(
        String(255)
    )  # The URL to the Galaxy instance, used for generating links in the notification
    # A bug in early 23.1 led to values being stored as json string, so we use this special type to process the result value twice.
    # content should always be a dict
    content: Mapped[Optional[bytes]] = mapped_column(DoubleEncodedJsonType)

    user_notification_associations: Mapped[List["UserNotificationAssociation"]] = relationship(
        back_populates="notification"
    )

    def __init__(self, source: str, category: str, variant: str, content):
        self.source = source
        self.category = category
        self.variant = variant
        self.content = content


class UserNotificationAssociation(Base, RepresentById):
    __tablename__ = "user_notification_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), index=True, nullable=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("notification.id"), index=True, nullable=True)
    seen_time: Mapped[Optional[datetime]]
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    update_time: Mapped[Optional[datetime]] = mapped_column(default=now, onupdate=now)

    user: Mapped["User"] = relationship(back_populates="all_notifications")
    notification: Mapped["Notification"] = relationship(back_populates="user_notification_associations")

    def __init__(self, user, notification):
        self.user = user
        ensure_object_added_to_session(self, object_in_session=user)
        self.notification = notification


def is_hda(d):
    return isinstance(d, HistoryDatasetAssociation)


class HistoryAudit(Base):
    __tablename__ = "history_audit"
    __table_args__ = (PrimaryKeyConstraint(sqlite_on_conflict="IGNORE"),)

    history_id: Mapped[int] = mapped_column(ForeignKey("history.id"), primary_key=True)
    update_time: Mapped[datetime] = mapped_column(default=now, primary_key=True)

    # This class should never be instantiated.
    # See https://github.com/galaxyproject/galaxy/pull/11914 for details.
    __init__ = None  # type: ignore[assignment]

    def __repr__(self):
        try:
            r = f"<galaxy.model.{self.__class__.__name__}({cached_id(self)}) at {hex(id(self))}>"
        except Exception:
            r = object.__repr__(self)
            log.exception("Caught exception attempting to generate repr for: %s", r)
        return r

    @classmethod
    def prune(cls, sa_session):
        latest_subq = (
            select(cls.history_id, func.max(cls.update_time).label("max_update_time"))
            .group_by(cls.history_id)
            .subquery()
        )
        not_latest_query = (
            select(cls.history_id, cls.update_time)
            .select_from(latest_subq)
            .join(
                cls,
                and_(
                    cls.update_time < latest_subq.columns.max_update_time,
                    cls.history_id == latest_subq.columns.history_id,
                ),
            )
            .subquery()
        )
        q = cls.__table__.delete().where(tuple_(cls.history_id, cls.update_time).in_(select(not_latest_query)))
        with sa_session() as session, session.begin():
            session.execute(q)


class History(Base, HasTags, Dictifiable, UsesAnnotations, HasName, Serializable, UsesCreateAndUpdateTime):
    __tablename__ = "history"
    __table_args__ = (Index("ix_history_slug", "slug", mysql_length=200),)

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    _update_time: Mapped[datetime] = mapped_column(
        "update_time", DateTime, index=True, default=now, onupdate=now, nullable=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    name: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    hid_counter: Mapped[Optional[int]] = mapped_column(default=1)
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    purged: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    importing: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    genome_build: Mapped[Optional[str]] = mapped_column(TrimmedString(40))
    importable: Mapped[Optional[bool]] = mapped_column(default=False)
    slug: Mapped[Optional[str]] = mapped_column(TEXT)
    published: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    preferred_object_store_id: Mapped[Optional[str]] = mapped_column(String(255))
    archived: Mapped[Optional[bool]] = mapped_column(index=True, default=False, server_default=false())
    archive_export_id: Mapped[Optional[int]] = mapped_column(ForeignKey("store_export_association.id"), default=None)

    datasets: Mapped[List["HistoryDatasetAssociation"]] = relationship(
        back_populates="history", order_by=lambda: asc(HistoryDatasetAssociation.hid)  # type: ignore[has-type]
    )
    exports: Mapped[List["JobExportHistoryArchive"]] = relationship(
        back_populates="history",
        primaryjoin=lambda: JobExportHistoryArchive.history_id == History.id,
        order_by=lambda: desc(JobExportHistoryArchive.id),
    )
    active_datasets: Mapped[List["HistoryDatasetAssociation"]] = relationship(
        primaryjoin=(
            lambda: and_(
                HistoryDatasetAssociation.history_id == History.id,  # type: ignore[arg-type]
                not_(HistoryDatasetAssociation.deleted),  # type: ignore[has-type]
            )
        ),
        order_by=lambda: asc(HistoryDatasetAssociation.hid),  # type: ignore[has-type]
        viewonly=True,
    )
    dataset_collections: Mapped[List["HistoryDatasetCollectionAssociation"]] = relationship(back_populates="history")
    active_dataset_collections: Mapped[List["HistoryDatasetCollectionAssociation"]] = relationship(
        primaryjoin=(
            lambda: (
                and_(
                    HistoryDatasetCollectionAssociation.history_id == History.id,
                    not_(HistoryDatasetCollectionAssociation.deleted),  # type: ignore[arg-type]
                )
            )
        ),
        order_by=lambda: asc(HistoryDatasetCollectionAssociation.hid),
        viewonly=True,
    )
    visible_datasets: Mapped[List["HistoryDatasetAssociation"]] = relationship(
        primaryjoin=(
            lambda: and_(
                HistoryDatasetAssociation.history_id == History.id,  # type: ignore[arg-type]
                not_(HistoryDatasetAssociation.deleted),  # type: ignore[has-type]
                HistoryDatasetAssociation.visible,  # type: ignore[has-type]
            )
        ),
        order_by=lambda: asc(HistoryDatasetAssociation.hid),  # type: ignore[has-type]
        viewonly=True,
    )
    visible_dataset_collections: Mapped[List["HistoryDatasetCollectionAssociation"]] = relationship(
        primaryjoin=(
            lambda: and_(
                HistoryDatasetCollectionAssociation.history_id == History.id,
                not_(HistoryDatasetCollectionAssociation.deleted),  # type: ignore[arg-type]
                HistoryDatasetCollectionAssociation.visible,  # type: ignore[arg-type]
            )
        ),
        order_by=lambda: asc(HistoryDatasetCollectionAssociation.hid),
        viewonly=True,
    )
    tags: Mapped[List["HistoryTagAssociation"]] = relationship(
        order_by=lambda: HistoryTagAssociation.id, back_populates="history"
    )
    annotations: Mapped[List["HistoryAnnotationAssociation"]] = relationship(
        order_by=lambda: HistoryAnnotationAssociation.id, back_populates="history"
    )
    ratings: Mapped[List["HistoryRatingAssociation"]] = relationship(
        order_by=lambda: HistoryRatingAssociation.id,
        back_populates="history",
    )
    default_permissions: Mapped[List["DefaultHistoryPermissions"]] = relationship(back_populates="history")
    users_shared_with: Mapped[List["HistoryUserShareAssociation"]] = relationship(back_populates="history")
    galaxy_sessions = relationship("GalaxySessionToHistoryAssociation", back_populates="history")
    workflow_invocations: Mapped[List["WorkflowInvocation"]] = relationship(back_populates="history")
    user: Mapped[Optional["User"]] = relationship(back_populates="histories")
    jobs: Mapped[List["Job"]] = relationship(back_populates="history")
    tool_requests: Mapped[List["ToolRequest"]] = relationship(back_populates="history")

    update_time = column_property(
        select(func.max(HistoryAudit.update_time)).where(HistoryAudit.history_id == id).scalar_subquery(),
    )
    users_shared_with_count = None
    average_rating = None

    # Set up proxy so that
    #   History.users_shared_with
    # returns a list of users that history is shared with.
    users_shared_with_dot_users = association_proxy("users_shared_with", "user")

    dict_collection_visible_keys = ["id", "name", "published", "deleted"]
    dict_element_visible_keys = [
        "id",
        "name",
        "archived",
        "create_time",
        "deleted",
        "empty",
        "genome_build",
        "hid_counter",
        "importable",
        "preferred_object_store_id",
        "purged",
        "published",
        "slug",
        "tags",
        "update_time",
        "username",
    ]
    default_name = "Unnamed history"

    def __init__(self, id=None, name=None, user=None):
        self.id = id
        self.name = name or History.default_name
        self.deleted = False
        self.purged = False
        self.importing = False
        self.published = False
        add_object_to_object_session(self, user)
        self.user = user
        # Objects to eventually add to history
        self._pending_additions = []
        self._item_by_hid_cache = None

    @reconstructor
    def init_on_load(self):
        # Restores properties that are not tracked in the database
        self._pending_additions = []

    def stage_addition(self, items):
        history_id = self.id
        for item in listify(items):
            item.history = self
            if history_id:
                item.history_id = history_id
            self._pending_additions.append(item)

    @property
    def empty(self):
        return self.hid_counter is None or self.hid_counter == 1

    @property
    def username(self):
        if user := self.user:
            return user.username
        return None

    @property
    def count(self):
        return self.hid_counter - 1

    def update(self):
        self._update_time = now()

    def add_pending_items(self, set_output_hid=True):
        # These are assumed to be either copies of existing datasets or new, empty datasets,
        # so we don't need to set the quota.
        self.add_datasets(
            object_session(self), self._pending_additions, set_hid=set_output_hid, quota=False, flush=False
        )
        self._pending_additions = []

    def _next_hid(self, n=1):
        """
        Generate next_hid from the database in a concurrency safe way:
        1. Retrieve hid_counter from database
        2. Increment hid_counter by n and store in database
        3. Return retrieved hid_counter.

        Handle with SQLAlchemy Core to keep this independent from current session state, except:
        expire hid_counter attribute, since its value in the session is no longer valid.
        """
        session = object_session(self)
        engine = session.bind
        table = self.__table__
        history_id = cached_id(self)
        update_stmt = update(table).where(table.c.id == history_id).values(hid_counter=table.c.hid_counter + n)
        update_returning_stmnt = update_stmt.returning(table.c.hid_counter)

        if engine.name != "sqlite":
            with engine.begin() as conn:
                hid = conn.execute(update_returning_stmnt).scalar() - n
        else:
            try:
                hid = session.execute(update_returning_stmnt).scalar() - n
            except (CompileError, OperationalError):
                # The RETURNING clause was added to SQLite in version 3.35.0.
                # Not using FOR UPDATE either, since that was added in 3.45.0,
                # and anyway does a whole-table lock
                select_stmt = select(table.c.hid_counter).where(table.c.id == history_id)
                hid = session.execute(select_stmt).scalar()
                session.execute(update_stmt)

        session.expire(self, ["hid_counter"])
        return hid

    def add_galaxy_session(self, galaxy_session, association=None):
        if association is None:
            self.galaxy_sessions.append(GalaxySessionToHistoryAssociation(galaxy_session, self))
        else:
            self.galaxy_sessions.append(association)

    def add_dataset(self, dataset, parent_id=None, genome_build=None, set_hid=True, quota=True):
        if isinstance(dataset, Dataset):
            dataset = HistoryDatasetAssociation(dataset=dataset)
            object_session(self).add(dataset)

            session = object_session(self)
            with transaction(session):
                session.commit()

        elif not isinstance(dataset, (HistoryDatasetAssociation, HistoryDatasetCollectionAssociation)):
            raise TypeError(
                "You can only add Dataset and HistoryDatasetAssociation instances to a history"
                f" ( you tried to add {str(dataset)} )."
            )
        is_dataset = is_hda(dataset)
        if parent_id:
            for data in self.datasets:
                if data.id == parent_id:
                    dataset.hid = data.hid
                    break
            else:
                if set_hid:
                    dataset.hid = self._next_hid()
        else:
            if set_hid:
                dataset.hid = self._next_hid()
        add_object_to_object_session(dataset, self)
        if quota and is_dataset and self.user:
            quota_source_info = dataset.dataset.quota_source_info
            if quota_source_info.use:
                self.user.adjust_total_disk_usage(dataset.quota_amount(self.user), quota_source_info.label)
        dataset.history = self
        if is_dataset and genome_build not in [None, "?"]:
            self.genome_build = genome_build
        dataset.history_id = self.id
        return dataset

    def add_datasets(
        self, sa_session, datasets, parent_id=None, genome_build=None, set_hid=True, quota=True, flush=False
    ):
        """Optimized version of add_dataset above that minimizes database
        interactions when adding many datasets and collections to history at once.
        """
        optimize = len(datasets) > 1 and parent_id is None and set_hid
        if optimize:
            self.__add_datasets_optimized(datasets, genome_build=genome_build)
            if quota and self.user:
                disk_usage = sum(d.get_total_size() for d in datasets if is_hda(d))
                if disk_usage:
                    quota_source_info = datasets[0].dataset.quota_source_info
                    if quota_source_info.use:
                        self.user.adjust_total_disk_usage(disk_usage, quota_source_info.label)
            sa_session.add_all(datasets)
            if flush:
                with transaction(sa_session):
                    sa_session.commit()
        else:
            for dataset in datasets:
                self.add_dataset(dataset, parent_id=parent_id, genome_build=genome_build, set_hid=set_hid, quota=quota)
                sa_session.add(dataset)
                if flush:
                    with transaction(sa_session):
                        sa_session.commit()

    def __add_datasets_optimized(self, datasets, genome_build=None):
        """Optimized version of add_dataset above that minimizes database
        interactions when adding many datasets to history at once under
        certain circumstances.
        """
        n = len(datasets)

        base_hid = self._next_hid(n=n)
        set_genome = genome_build not in [None, "?"]
        for i, dataset in enumerate(datasets):
            dataset.hid = base_hid + i
            dataset.history = self
            dataset.history_id = cached_id(self)
            if set_genome and is_hda(dataset):
                self.genome_build = genome_build
        return datasets

    def add_dataset_collection(self, history_dataset_collection, set_hid=True):
        if set_hid:
            history_dataset_collection.hid = self._next_hid()
        add_object_to_object_session(history_dataset_collection, self)
        history_dataset_collection.history = self
        # TODO: quota?
        self.dataset_collections.append(history_dataset_collection)
        return history_dataset_collection

    def copy(self, name=None, target_user=None, activatable=False, all_datasets=False):
        """
        Return a copy of this history using the given `name` and `target_user`.
        If `activatable`, copy only non-deleted datasets. If `all_datasets`, copy
        non-deleted, deleted, and purged datasets.
        """
        name = name or self.name
        applies_to_quota = target_user != self.user

        # Create new history.
        new_history = History(name=name, user=target_user)
        db_session = object_session(self)
        db_session.add(new_history)
        db_session.flush([new_history])

        # copy history tags and annotations (if copying user is not anonymous)
        if target_user:
            self.copy_item_annotation(db_session, self.user, self, target_user, new_history)
            new_history.copy_tags_from(target_user=target_user, source=self)

        # Copy HDAs.
        if activatable:
            hdas = self.activatable_datasets
        elif all_datasets:
            hdas = self.datasets
        else:
            hdas = self.active_datasets
        for hda in hdas:
            # Copy HDA.
            new_hda = hda.copy(flush=False)
            new_history.add_dataset(new_hda, set_hid=False, quota=applies_to_quota)

            if target_user:
                new_hda.copy_item_annotation(db_session, self.user, hda, target_user, new_hda)
                new_hda.copy_tags_from(target_user, hda)

        # Copy history dataset collections
        if all_datasets:
            hdcas = self.dataset_collections
        else:
            hdcas = self.active_dataset_collections
        for hdca in hdcas:
            new_hdca = hdca.copy(flush=False, element_destination=new_history, set_hid=False, minimize_copies=True)
            new_history.add_dataset_collection(new_hdca, set_hid=False)
            db_session.add(new_hdca)

            if target_user:
                new_hdca.copy_item_annotation(db_session, self.user, hdca, target_user, new_hdca)
                new_hdca.copy_tags_from(target_user, hdca)

        new_history.hid_counter = self.hid_counter
        with transaction(db_session):
            db_session.commit()

        return new_history

    def get_dataset_by_hid(self, hid):
        if self._item_by_hid_cache is None:
            self._item_by_hid_cache = {dataset.hid: dataset for dataset in self.datasets}
        return self._item_by_hid_cache.get(hid)

    @property
    def has_possible_members(self):
        return True

    @property
    def activatable_datasets(self):
        # This needs to be a list
        return [hda for hda in self.datasets if not hda.dataset.deleted]

    def _serialize(self, id_encoder, serialization_options):
        history_attrs = dict_for(
            self,
            create_time=self.create_time.__str__(),
            update_time=self.update_time.__str__(),
            name=unicodify(self.name),
            hid_counter=self.hid_counter,
            genome_build=self.genome_build,
            annotation=unicodify(get_item_annotation_str(object_session(self), self.user, self)),
            tags=self.make_tag_string_list(),
        )
        serialization_options.attach_identifier(id_encoder, self, history_attrs)
        return history_attrs

    def to_dict(self, view="collection", value_mapper=None):
        # Get basic value.
        rval = super().to_dict(view=view, value_mapper=value_mapper)

        if view == "element":
            rval["size"] = int(self.disk_size)

        return rval

    @property
    def latest_export(self):
        exports = self.exports
        return exports and exports[0]

    def unhide_datasets(self):
        for dataset in self.datasets:
            dataset.mark_unhidden()

    def resume_paused_jobs(self):
        job = None
        for job in self.paused_jobs:
            job.resume(flush=False)
        if job is not None:
            # We'll flush once if there was a paused job
            session = object_session(job)
            with transaction(session):
                session.commit()

    @property
    def paused_jobs(self):
        stmt = select(Job).where(Job.history_id == self.id, Job.state == Job.states.PAUSED)
        return object_session(self).scalars(stmt).all()

    @hybrid.hybrid_property
    def disk_size(self):
        """
        Return the size in bytes of this history by summing the 'total_size's of
        all non-purged, unique datasets within it.
        """
        # non-.expression part of hybrid.hybrid_property: called when an instance is the namespace (not the class)
        subq = (
            select(HistoryDatasetAssociation.dataset_id, Dataset.total_size)
            .join(Dataset)
            .where(HistoryDatasetAssociation.history_id == self.id)
            .where(HistoryDatasetAssociation.purged != true())
            .where(Dataset.purged != true())
            .distinct()  # unique datasets only
            .subquery()
        )
        stmt = select(func.sum(subq.c.total_size))
        return object_session(self).scalar(stmt) or 0

    @disk_size.expression  # type: ignore[no-redef]
    def disk_size(cls):
        """
        Return a query scalar that will get any history's size in bytes by summing
        the 'total_size's of all non-purged, unique datasets within it.
        """
        # .expression acts as a column_property and should return a scalar
        # first, get the distinct datasets within a history that are not purged
        hda_to_dataset_join = join(
            HistoryDatasetAssociation, Dataset, HistoryDatasetAssociation.dataset_id == Dataset.id
        )
        distinct_datasets = (
            select(
                # use labels here to better access from the query above
                HistoryDatasetAssociation.history_id.label("history_id"),
                Dataset.total_size.label("dataset_size"),
                Dataset.id.label("dataset_id"),
            )
            .where(HistoryDatasetAssociation.purged != true())
            .where(Dataset.purged != true())
            .select_from(hda_to_dataset_join)
            # TODO: slow (in general) but most probably here - index total_size for easier sorting/distinct?
            .distinct()
        )
        # postgres needs an alias on FROM
        distinct_datasets_alias = aliased(distinct_datasets.subquery(), name="datasets")
        # then, bind as property of history using the cls.id
        size_query = (
            select(func.coalesce(func.sum(distinct_datasets_alias.c.dataset_size), 0))
            .select_from(distinct_datasets_alias)
            .where(distinct_datasets_alias.c.history_id == cls.id)
        )
        # label creates a scalar
        return size_query.label("disk_size")

    @property
    def disk_nice_size(self):
        """Returns human readable size of history on disk."""
        return galaxy.util.nice_size(self.disk_size)

    def _active_dataset_and_roles_query(self):
        return (
            select(HistoryDatasetAssociation)
            .where(HistoryDatasetAssociation.history_id == self.id)
            .where(not_(HistoryDatasetAssociation.deleted))
            .order_by(HistoryDatasetAssociation.hid.asc())
            .options(
                joinedload(HistoryDatasetAssociation.dataset)
                .joinedload(Dataset.actions)
                .joinedload(DatasetPermissions.role),
                joinedload(HistoryDatasetAssociation.tags),
            )
        )

    @property
    def active_datasets_and_roles(self):
        if not hasattr(self, "_active_datasets_and_roles"):
            stmt = self._active_dataset_and_roles_query()
            self._active_datasets_and_roles = object_session(self).scalars(stmt).unique().all()
        return self._active_datasets_and_roles

    @property
    def active_visible_datasets_and_roles(self):
        if not hasattr(self, "_active_visible_datasets_and_roles"):
            stmt = self._active_dataset_and_roles_query().where(HistoryDatasetAssociation.visible)
            self._active_visible_datasets_and_roles = object_session(self).scalars(stmt).unique().all()
        return self._active_visible_datasets_and_roles

    @property
    def active_visible_dataset_collections(self):
        if not hasattr(self, "_active_visible_dataset_collections"):
            stmt = (
                select(HistoryDatasetCollectionAssociation)
                .where(HistoryDatasetCollectionAssociation.history_id == self.id)
                .where(not_(HistoryDatasetCollectionAssociation.deleted))
                .where(HistoryDatasetCollectionAssociation.visible)
                .order_by(HistoryDatasetCollectionAssociation.hid.asc())
                .options(
                    joinedload(HistoryDatasetCollectionAssociation.collection),
                    joinedload(HistoryDatasetCollectionAssociation.tags),
                )
            )
            self._active_visible_dataset_collections = object_session(self).scalars(stmt).unique().all()
        return self._active_visible_dataset_collections

    @property
    def active_contents(self):
        """Return all active contents ordered by hid."""
        return self.contents_iter(types=["dataset", "dataset_collection"], deleted=False, visible=True)

    def contents_iter(self, **kwds):
        """
        Fetch filtered list of contents of history.
        """
        default_contents_types = [
            "dataset",
        ]
        types = kwds.get("types", default_contents_types)
        iters = []
        if "dataset" in types:
            iters.append(self.__dataset_contents_iter(**kwds))
        if "dataset_collection" in types:
            iters.append(self.__collection_contents_iter(**kwds))
        return galaxy.util.merge_sorted_iterables(operator.attrgetter("hid"), *iters)

    def __dataset_contents_iter(self, **kwds):
        return self.__filter_contents(HistoryDatasetAssociation, **kwds)

    def __collection_contents_iter(self, **kwds):
        return self.__filter_contents(HistoryDatasetCollectionAssociation, **kwds)

    def __filter_contents(self, content_class, **kwds):
        session = object_session(self)
        stmt = select(content_class).where(content_class.history_id == self.id).order_by(content_class.hid.asc())

        deleted = galaxy.util.string_as_bool_or_none(kwds.get("deleted", None))
        if deleted is not None:
            stmt = stmt.where(content_class.deleted == deleted)

        visible = galaxy.util.string_as_bool_or_none(kwds.get("visible", None))
        if visible is not None:
            stmt = stmt.where(content_class.visible == visible)

        if "object_store_ids" in kwds:
            if content_class == HistoryDatasetAssociation:
                stmt = stmt.join(content_class.dataset).where(Dataset.object_store_id.in_(kwds.get("object_store_ids")))
            # else ignoring object_store_ids on HDCAs...

        if "ids" in kwds:
            assert "object_store_ids" not in kwds
            ids = kwds["ids"]
            max_in_filter_length = kwds.get("max_in_filter_length", MAX_IN_FILTER_LENGTH)
            if len(ids) < max_in_filter_length:
                stmt = stmt.where(content_class.id.in_(ids))
            else:
                return (content for content in session.scalars(stmt) if content.id in ids)

        return session.scalars(stmt)


class UserShareAssociation(RepresentById):
    user: Mapped[User]


class HistoryUserShareAssociation(Base, UserShareAssociation):
    __tablename__ = "history_user_share_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    history_id: Mapped[int] = mapped_column(ForeignKey("history.id"), index=True, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), index=True, nullable=True)
    user: Mapped["User"] = relationship()
    history: Mapped["History"] = relationship(back_populates="users_shared_with")


class UserRoleAssociation(Base, RepresentById):
    __tablename__ = "user_role_association"
    __table_args__ = (UniqueConstraint("user_id", "role_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), index=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)

    user: Mapped["User"] = relationship(back_populates="roles")
    role: Mapped["Role"] = relationship(back_populates="users")

    def __init__(self, user, role):
        add_object_to_object_session(self, user)
        self.user = user
        self.role = role


class GroupRoleAssociation(Base, RepresentById):
    __tablename__ = "group_role_association"
    __table_args__ = (UniqueConstraint("group_id", "role_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("galaxy_group.id"), index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), index=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    group: Mapped["Group"] = relationship(back_populates="roles")
    role: Mapped["Role"] = relationship(back_populates="groups")

    def __init__(self, group, role):
        self.group = group
        ensure_object_added_to_session(self, object_in_session=group)
        self.role = role


class Role(Base, Dictifiable, RepresentById):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    _name: Mapped[str] = mapped_column("name", String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(TEXT)
    type: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    dataset_actions: Mapped[List["DatasetPermissions"]] = relationship(back_populates="role")
    groups: Mapped[List["GroupRoleAssociation"]] = relationship(back_populates="role")
    users: Mapped[List["UserRoleAssociation"]] = relationship(back_populates="role")

    dict_collection_visible_keys = ["id", "name"]
    dict_element_visible_keys = ["id", "name", "description", "type"]
    private_id = None

    class types(str, Enum):
        PRIVATE = "private"
        SYSTEM = "system"
        USER = "user"
        ADMIN = "admin"
        SHARING = "sharing"

    @staticmethod
    def default_name(role_type):
        return f"{role_type.value} role"

    @hybrid_property
    def name(self):
        if self.type == Role.types.PRIVATE:
            user_assocs = self.users
            assert len(user_assocs) == 1, f"Did not find exactly one user for private role {self}"
            return user_assocs[0].user.email
        else:
            return self._name

    @name.setter  # type:ignore[no-redef]  # property setter
    def name(self, name):
        self._name = name

    def __init__(self, name=None, description=None, type=types.SYSTEM, deleted=False):
        self.name = name or Role.default_name(type)
        self.description = description
        self.type = type
        self.deleted = deleted


class UserQuotaSourceUsage(Base, Dictifiable, RepresentById):
    __tablename__ = "user_quota_source_usage"
    __table_args__ = (UniqueConstraint("user_id", "quota_source_label", name="uqsu_unique_label_per_user"),)

    dict_element_visible_keys = ["disk_usage", "quota_source_label"]

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    quota_source_label: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    # user had an index on disk_usage - does that make any sense? -John
    disk_usage: Mapped[Decimal] = mapped_column(Numeric(15, 0), default=0)
    user: Mapped[Optional["User"]] = relationship(back_populates="quota_source_usages")


class UserQuotaAssociation(Base, Dictifiable, RepresentById):
    __tablename__ = "user_quota_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), index=True, nullable=True)
    quota_id: Mapped[int] = mapped_column(ForeignKey("quota.id"), index=True, nullable=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    user: Mapped["User"] = relationship(back_populates="quotas")
    quota: Mapped["Quota"] = relationship(back_populates="users")

    dict_element_visible_keys = ["user"]

    def __init__(self, user, quota):
        add_object_to_object_session(self, user)
        self.user = user
        self.quota = quota


class GroupQuotaAssociation(Base, Dictifiable, RepresentById):
    __tablename__ = "group_quota_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("galaxy_group.id"), index=True, nullable=True)
    quota_id: Mapped[int] = mapped_column(ForeignKey("quota.id"), index=True, nullable=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    group: Mapped["Group"] = relationship(back_populates="quotas")
    quota: Mapped["Quota"] = relationship(back_populates="groups")

    dict_element_visible_keys = ["group"]

    def __init__(self, group, quota):
        add_object_to_object_session(self, group)
        self.group = group
        self.quota = quota


class Quota(Base, Dictifiable, RepresentById):
    __tablename__ = "quota"
    __table_args__ = (Index("ix_quota_quota_source_label", "quota_source_label"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), index=True, unique=True)
    description: Mapped[Optional[str]] = mapped_column(TEXT)
    bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    operation: Mapped[Optional[str]] = mapped_column(String(8))
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    quota_source_label: Mapped[Optional[str]] = mapped_column(String(32), default=None)
    default: Mapped[List["DefaultQuotaAssociation"]] = relationship("DefaultQuotaAssociation", back_populates="quota")
    groups: Mapped[List["GroupQuotaAssociation"]] = relationship(back_populates="quota")
    users: Mapped[List["UserQuotaAssociation"]] = relationship(back_populates="quota")

    dict_collection_visible_keys = ["id", "name", "quota_source_label"]
    dict_element_visible_keys = [
        "id",
        "name",
        "description",
        "bytes",
        "operation",
        "display_amount",
        "default",
        "users",
        "groups",
        "quota_source_label",
    ]
    valid_operations = ("+", "-", "=")

    def __init__(self, name=None, description=None, amount=0, operation="=", quota_source_label=None):
        self.name = name
        self.description = description
        if amount is None:
            self.bytes = -1
        else:
            self.bytes = amount
        self.operation = operation
        self.quota_source_label = quota_source_label

    def get_amount(self):
        if self.bytes == -1:
            return None
        return self.bytes

    def set_amount(self, amount):
        if amount is None:
            self.bytes = -1
        else:
            self.bytes = amount

    amount = property(get_amount, set_amount)

    @property
    def display_amount(self):
        if self.bytes == -1:
            return "unlimited"
        else:
            return galaxy.util.nice_size(self.bytes)


class DefaultQuotaAssociation(Base, Dictifiable, RepresentById):
    __tablename__ = "default_quota_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(32))
    quota_id: Mapped[int] = mapped_column(ForeignKey("quota.id"), index=True, nullable=True)
    quota: Mapped["Quota"] = relationship(back_populates="default")

    dict_element_visible_keys = ["type"]

    class types(str, Enum):
        UNREGISTERED = "unregistered"
        REGISTERED = "registered"

    def __init__(self, type, quota):
        assert type in self.types.__members__.values(), "Invalid type"
        self.type = type
        self.quota = quota
        ensure_object_added_to_session(self, object_in_session=quota)


class DatasetPermissions(Base, RepresentById):
    __tablename__ = "dataset_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(TEXT)
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dataset.id"), index=True)
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("role.id"), index=True)
    dataset: Mapped[Optional["Dataset"]] = relationship(back_populates="actions")
    role: Mapped[Optional["Role"]] = relationship(back_populates="dataset_actions")

    def __init__(self, action, dataset, role=None, role_id=None):
        self.action = action
        add_object_to_object_session(self, dataset)
        self.dataset = dataset
        if role is not None:
            self.role = role
        else:
            self.role_id = role_id


class LibraryPermissions(Base, RepresentById):
    __tablename__ = "library_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(TEXT)
    library_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library.id"), index=True)
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("role.id"), index=True)
    library: Mapped[Optional["Library"]] = relationship(back_populates="actions")
    role: Mapped[Optional["Role"]] = relationship()

    def __init__(self, action, library_item, role):
        self.action = action
        if isinstance(library_item, Library):
            self.library = library_item
            ensure_object_added_to_session(self, object_in_session=library_item)
        else:
            raise Exception(f"Invalid Library specified: {library_item.__class__.__name__}")
        self.role = role


class LibraryFolderPermissions(Base, RepresentById):
    __tablename__ = "library_folder_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(TEXT)
    library_folder_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library_folder.id"), index=True)
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("role.id"), index=True)
    folder: Mapped[Optional["LibraryFolder"]] = relationship(back_populates="actions")
    role: Mapped[Optional["Role"]] = relationship()

    def __init__(self, action, library_item, role):
        self.action = action
        if isinstance(library_item, LibraryFolder):
            self.folder = library_item
            ensure_object_added_to_session(self, object_in_session=library_item)
        else:
            raise Exception(f"Invalid LibraryFolder specified: {library_item.__class__.__name__}")
        self.role = role


class LibraryDatasetPermissions(Base, RepresentById):
    __tablename__ = "library_dataset_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(TEXT)
    library_dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library_dataset.id"), index=True)
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("role.id"), index=True)
    library_dataset: Mapped[Optional["LibraryDataset"]] = relationship(back_populates="actions")
    role: Mapped[Optional["Role"]] = relationship()

    def __init__(self, action, library_item, role):
        self.action = action
        if isinstance(library_item, LibraryDataset):
            self.library_dataset = library_item
            ensure_object_added_to_session(self, object_in_session=library_item)
        else:
            raise Exception(f"Invalid LibraryDataset specified: {library_item.__class__.__name__}")
        self.role = role


class LibraryDatasetDatasetAssociationPermissions(Base, RepresentById):
    __tablename__ = "library_dataset_dataset_association_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(TEXT)
    library_dataset_dataset_association_id: Mapped[int] = mapped_column(
        ForeignKey("library_dataset_dataset_association.id"), index=True, nullable=True
    )
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("role.id"), index=True)
    library_dataset_dataset_association: Mapped["LibraryDatasetDatasetAssociation"] = relationship(
        back_populates="actions"
    )
    role: Mapped[Optional["Role"]] = relationship()

    def __init__(self, action, library_item, role):
        self.action = action
        if isinstance(library_item, LibraryDatasetDatasetAssociation):
            add_object_to_object_session(self, library_item)
            self.library_dataset_dataset_association = library_item
        else:
            raise Exception(f"Invalid LibraryDatasetDatasetAssociation specified: {library_item.__class__.__name__}")
        self.role = role


class DefaultUserPermissions(Base, RepresentById):
    __tablename__ = "default_user_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    action: Mapped[Optional[str]] = mapped_column(TEXT)
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("role.id"), index=True)
    user: Mapped[Optional["User"]] = relationship(back_populates="default_permissions")
    role: Mapped[Optional["Role"]] = relationship()

    def __init__(self, user, action, role):
        add_object_to_object_session(self, user)
        self.user = user
        self.action = action
        self.role = role


class DefaultHistoryPermissions(Base, RepresentById):
    __tablename__ = "default_history_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    history_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history.id"), index=True)
    action: Mapped[Optional[str]] = mapped_column(TEXT)
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("role.id"), index=True)
    history: Mapped[Optional["History"]] = relationship(back_populates="default_permissions")
    role: Mapped[Optional["Role"]] = relationship()

    def __init__(self, history, action, role):
        add_object_to_object_session(self, history)
        self.history = history
        self.action = action
        self.role = role


class StorableObject:
    def flush(self):
        if sa_session := object_session(self):
            with transaction(sa_session):
                sa_session.commit()


def setup_global_object_store_for_models(object_store: "BaseObjectStore") -> None:
    Dataset.object_store = object_store


class Dataset(Base, StorableObject, Serializable):
    __tablename__ = "dataset"
    __table_args__ = (UniqueConstraint("uuid", name="uq_uuid_column"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(index=True, default=now, onupdate=now, nullable=True)
    state: Mapped[Optional[str]] = mapped_column(TrimmedString(64), index=True)
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    purged: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    purgable: Mapped[Optional[bool]] = mapped_column(default=True)
    object_store_id: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    external_filename: Mapped[Optional[str]] = mapped_column(TEXT)
    _extra_files_path: Mapped[Optional[str]] = mapped_column(TEXT)
    created_from_basename: Mapped[Optional[str]] = mapped_column(TEXT)
    file_size: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 0))
    total_size: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 0))
    uuid: Mapped[Optional[Union[UUID, str]]] = mapped_column(UUIDType(), unique=True)

    actions: Mapped[List["DatasetPermissions"]] = relationship(back_populates="dataset")
    job: Mapped[Optional["Job"]] = relationship(primaryjoin=(lambda: Dataset.job_id == Job.id))
    active_history_associations: Mapped[List["HistoryDatasetAssociation"]] = relationship(
        primaryjoin=(
            lambda: and_(
                Dataset.id == HistoryDatasetAssociation.dataset_id,  # type: ignore[attr-defined]
                HistoryDatasetAssociation.deleted == false(),  # type: ignore[has-type]
                HistoryDatasetAssociation.purged == false(),  # type: ignore[arg-type]
            )
        ),
        viewonly=True,
    )
    purged_history_associations: Mapped[List["HistoryDatasetAssociation"]] = relationship(
        primaryjoin=(
            lambda: and_(
                Dataset.id == HistoryDatasetAssociation.dataset_id,  # type: ignore[attr-defined]
                HistoryDatasetAssociation.purged == true(),  # type: ignore[arg-type]
            )
        ),
        viewonly=True,
    )
    active_library_associations: Mapped[List["LibraryDatasetDatasetAssociation"]] = relationship(
        primaryjoin=(
            lambda: and_(
                Dataset.id == LibraryDatasetDatasetAssociation.dataset_id,  # type: ignore[attr-defined]
                LibraryDatasetDatasetAssociation.deleted == false(),  # type: ignore[has-type]
            )
        ),
        viewonly=True,
    )
    hashes: Mapped[List["DatasetHash"]] = relationship(back_populates="dataset")
    sources: Mapped[List["DatasetSource"]] = relationship(back_populates="dataset")
    history_associations: Mapped[List["HistoryDatasetAssociation"]] = relationship(back_populates="dataset")
    library_associations: Mapped[List["LibraryDatasetDatasetAssociation"]] = relationship(
        primaryjoin=(lambda: LibraryDatasetDatasetAssociation.table.c.dataset_id == Dataset.id),
        back_populates="dataset",
    )

    # failed_metadata is only valid as DatasetInstance state currently
    states = DatasetState

    non_ready_states = (states.NEW, states.UPLOAD, states.QUEUED, states.RUNNING, states.SETTING_METADATA)
    ready_states = tuple(set(states.__members__.values()) - set(non_ready_states))
    valid_input_states = tuple(
        set(states.__members__.values()) - {states.ERROR, states.DISCARDED, states.FAILED_METADATA}
    )
    no_data_states = (states.PAUSED, states.DEFERRED, states.DISCARDED, *non_ready_states)
    terminal_states = (
        states.OK,
        states.EMPTY,
        states.ERROR,
        states.DEFERRED,
        states.DISCARDED,
        states.FAILED_METADATA,
    )

    class conversion_messages(str, Enum):
        PENDING = "pending"
        NO_DATA = "no data"
        NO_CHROMOSOME = "no chromosome"
        NO_CONVERTER = "no converter"
        NO_TOOL = "no tool"
        DATA = "data"
        ERROR = "error"
        OK = "ok"

    permitted_actions = get_permitted_actions(filter="DATASET")
    file_path = "/tmp/"
    object_store: ClassVar[Optional["BaseObjectStore"]] = (
        None  # This get initialized in mapping.py (method init) by app.py
    )
    engine = None

    def __init__(
        self,
        id=None,
        state=None,
        external_filename=None,
        extra_files_path=None,
        file_size=None,
        purgable=True,
        uuid=None,
    ):
        self.id = id
        self.uuid = get_uuid(uuid)
        self.state = state
        self.deleted = False
        self.purged = False
        self.purgable = purgable
        self.external_filename = external_filename
        self.external_extra_files_path = None
        self._extra_files_path = extra_files_path
        self.file_size = file_size
        self.sources = []
        self.hashes = []

    @property
    def is_new(self):
        return self.state == self.states.NEW

    def in_ready_state(self):
        return self.state in self.ready_states

    @property
    def shareable(self) -> bool:
        """Return True if placed into an objectstore not labeled as ``private``."""
        if self.external_filename:
            return True
        else:
            object_store = self._assert_object_store_set()
            return not object_store.is_private(self)

    def ensure_shareable(self):
        if not self.shareable:
            raise Exception(CANNOT_SHARE_PRIVATE_DATASET_MESSAGE)

    def get_file_name(self, sync_cache: bool = True) -> str:
        if self.purged:
            log.warning(f"Attempt to get file name of purged dataset {self.id}")
            return ""
        if not self.external_filename:
            object_store = self._assert_object_store_set()
            if object_store.exists(self):
                file_name = object_store.get_filename(self, sync_cache=sync_cache)
            else:
                file_name = ""
            if not file_name and self.state not in (self.states.NEW, self.states.QUEUED):
                # Queued datasets can be assigned an object store and have a filename, but they aren't guaranteed to.
                # Anything after queued should have a file name.
                log.warning(f"Failed to determine file name for dataset {self.id} in state {self.state}")
            return file_name
        else:
            filename = self.external_filename
        # Make filename absolute
        return os.path.abspath(filename)

    @property
    def quota_source_label(self):
        return self.quota_source_info.label

    @property
    def quota_source_info(self):
        object_store_id = self.object_store_id
        quota_source_map = self.object_store.get_quota_source_map()
        return quota_source_map.get_quota_source_info(object_store_id)

    @property
    def device_source_label(self):
        return self.device_source_info.label

    @property
    def device_source_info(self):
        object_store_id = self.object_store_id
        device_source_map = self.object_store.get_quota_source_map()
        return device_source_map.get_device_source_info(object_store_id)

    def set_file_name(self, filename):
        if not filename:
            self.external_filename = None
        else:
            self.external_filename = filename

    def _assert_object_store_set(self) -> "BaseObjectStore":
        assert self.object_store is not None, "Object Store has not been initialized"
        return self.object_store

    def get_extra_files_path(self) -> str:
        # Unlike get_file_name - external_extra_files_path is not backed by an
        # actual database column so if SA instantiates this object - the
        # attribute won't exist yet.
        if not getattr(self, "external_extra_files_path", None):
            object_store = self._assert_object_store_set()
            if object_store.exists(self, dir_only=True, extra_dir=self._extra_files_rel_path):
                return object_store.get_filename(self, dir_only=True, extra_dir=self._extra_files_rel_path)
            return object_store.construct_path(self, dir_only=True, extra_dir=self._extra_files_rel_path, in_cache=True)
        else:
            return os.path.abspath(self.external_extra_files_path)

    def create_extra_files_path(self):
        if not self.extra_files_path_exists():
            self.object_store.create(self, dir_only=True, extra_dir=self._extra_files_rel_path)

    def set_extra_files_path(self, extra_files_path):
        if not extra_files_path:
            self.external_extra_files_path = None
        else:
            self.external_extra_files_path = extra_files_path

    extra_files_path = property(get_extra_files_path, set_extra_files_path)

    def extra_files_path_exists(self):
        return self.object_store.exists(self, extra_dir=self._extra_files_rel_path, dir_only=True)

    @property
    def store_by(self):
        store_by = self.object_store.get_store_by(self)
        return store_by

    def extra_files_path_name_from(self, object_store):
        if (store_by := self.store_by) is not None:
            return f"dataset_{getattr(self, store_by)}_files"
        else:
            return None

    @property
    def extra_files_path_name(self):
        return self.extra_files_path_name_from(self.object_store)

    @property
    def _extra_files_rel_path(self):
        return self._extra_files_path or self.extra_files_path_name

    def _calculate_size(self) -> int:
        if self.external_filename:
            try:
                return os.path.getsize(self.external_filename)
            except OSError:
                return 0
        assert self.object_store
        return self.object_store.size(self)

    @overload
    def get_size(self, nice_size: Literal[False], calculate_size: bool = True) -> int: ...

    @overload
    def get_size(self, nice_size: Literal[True], calculate_size: bool = True) -> str: ...

    def get_size(self, nice_size: bool = False, calculate_size: bool = True) -> Union[int, str]:
        """Returns the size of the data on disk"""
        if self.file_size:
            if nice_size:
                return galaxy.util.nice_size(self.file_size)
            else:
                return cast(int, self.file_size)
        elif calculate_size:
            # Hopefully we only reach this branch in sessionless mode
            if nice_size:
                return galaxy.util.nice_size(self._calculate_size())
            else:
                return self._calculate_size()
        else:
            return cast(int, self.file_size) or 0

    def set_size(self, no_extra_files=False):
        """Sets the size of the data on disk.

        If the caller is sure there are no extra files, pass no_extra_files as True to optimize subsequent
        calls to get_total_size or set_total_size - potentially avoiding both a database flush and check against
        the file system.
        """
        if not self.file_size:
            self.file_size = self._calculate_size()
            if no_extra_files:
                self.total_size = self.file_size

    def get_total_size(self):
        if self.total_size is not None:
            return self.total_size
        # for backwards compatibility, set if unset
        self.set_total_size()
        db_session = object_session(self)
        with transaction(db_session):
            db_session.commit()
        return self.total_size

    def set_total_size(self):
        if self.file_size is None:
            self.set_size()
        self.total_size = self.file_size or 0
        if (rel_path := self._extra_files_rel_path) is not None:
            if self.object_store.exists(self, extra_dir=rel_path, dir_only=True):
                for root, _, files in os.walk(self.extra_files_path):
                    self.total_size += sum(
                        os.path.getsize(os.path.join(root, file))
                        for file in files
                        if os.path.exists(os.path.join(root, file))
                    )
        return self.total_size

    def has_data(self):
        """Detects whether there is any data"""
        return not self.is_new and self.get_size() > 0

    def mark_deleted(self):
        self.deleted = True

    # FIXME: sqlalchemy will replace this
    def _delete(self):
        """Remove the file that corresponds to this data"""
        self.object_store.delete(self)

    @property
    def user_can_purge(self):
        return (
            self.purged is False
            and not bool(self.library_associations)
            and len(self.history_associations) == len(self.purged_history_associations)
        )

    def full_delete(self):
        """Remove the file and extra files, marks deleted and purged"""
        # os.unlink( self.file_name )
        try:
            self.object_store.delete(self)
        except galaxy.exceptions.ObjectNotFound:
            pass
        if (rel_path := self._extra_files_rel_path) is not None:
            if self.object_store.exists(self, extra_dir=rel_path, dir_only=True):
                self.object_store.delete(self, entire_dir=True, extra_dir=rel_path, dir_only=True)
        # TODO: purge metadata files
        self.deleted = True
        self.purged = True

    def get_access_roles(self, security_agent):
        roles = []
        for dp in self.actions:
            if dp.action == security_agent.permitted_actions.DATASET_ACCESS.action:
                roles.append(dp.role)
        return roles

    def get_manage_permissions_roles(self, security_agent):
        roles = []
        for dp in self.actions:
            if dp.action == security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
                roles.append(dp.role)
        return roles

    def has_manage_permissions_roles(self, security_agent):
        for dp in self.actions:
            if dp.action == security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
                return True
        return False

    def _serialize(self, id_encoder, serialization_options):
        # serialize Dataset objects only for jobs that can actually modify these models.
        assert serialization_options.serialize_dataset_objects

        def to_int(n) -> Optional[int]:
            return int(n) if n is not None else None

        rval = dict_for(
            self,
            state=self.state,
            deleted=self.deleted,
            purged=self.purged,
            external_filename=self.external_filename,
            _extra_files_path=self._extra_files_path,
            file_size=to_int(self.file_size),
            object_store_id=self.object_store_id,
            total_size=to_int(self.total_size),
            created_from_basename=self.created_from_basename,
            uuid=str(self.uuid or "") or None,
            hashes=[h.serialize(id_encoder, serialization_options) for h in self.hashes],
            sources=[s.serialize(id_encoder, serialization_options) for s in self.sources],
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval


class DatasetSource(Base, Dictifiable, Serializable):
    __tablename__ = "dataset_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dataset.id"), index=True)
    source_uri: Mapped[Optional[str]] = mapped_column(TEXT)
    extra_files_path: Mapped[Optional[str]] = mapped_column(TEXT)
    transform: Mapped[Optional[TRANSFORM_ACTIONS]] = mapped_column(MutableJSONType)
    dataset: Mapped[Optional["Dataset"]] = relationship(back_populates="sources")
    hashes: Mapped[List["DatasetSourceHash"]] = relationship(back_populates="source")
    dict_collection_visible_keys = ["id", "source_uri", "extra_files_path", "transform"]
    dict_element_visible_keys = [
        "id",
        "source_uri",
        "extra_files_path",
        "transform",
    ]  # TODO: implement to_dict and add hashes...

    def _serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            source_uri=self.source_uri,
            extra_files_path=self.extra_files_path,
            transform=self.transform,
            hashes=[h.serialize(id_encoder, serialization_options) for h in self.hashes],
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def copy(self) -> "DatasetSource":
        new_source = DatasetSource()
        new_source.source_uri = self.source_uri
        new_source.extra_files_path = self.extra_files_path
        new_source.transform = self.transform
        new_source.hashes = [h.copy() for h in self.hashes]
        return new_source


class HasHashFunctionName:
    hash_function: Mapped[Optional[str]]

    @property
    def hash_func_name(self) -> HashFunctionNameEnum:
        as_str = self.hash_function
        assert as_str
        return HashFunctionNameEnum(self.hash_function)


class DatasetSourceHash(Base, Serializable, HasHashFunctionName):
    __tablename__ = "dataset_source_hash"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dataset_source.id"), index=True)
    hash_function: Mapped[Optional[str]] = mapped_column(TEXT)
    hash_value: Mapped[Optional[str]] = mapped_column(TEXT)
    source: Mapped[Optional["DatasetSource"]] = relationship(back_populates="hashes")

    def _serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            hash_function=self.hash_function,
            hash_value=self.hash_value,
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def copy(self) -> "DatasetSourceHash":
        new_hash = DatasetSourceHash()
        new_hash.hash_function = self.hash_function
        new_hash.hash_value = self.hash_value
        return new_hash


class DatasetHash(Base, Dictifiable, Serializable, HasHashFunctionName):
    __tablename__ = "dataset_hash"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dataset.id"), index=True)
    hash_function: Mapped[Optional[str]] = mapped_column(TEXT)
    hash_value: Mapped[Optional[str]] = mapped_column(TEXT)
    extra_files_path: Mapped[Optional[str]] = mapped_column(TEXT)
    dataset: Mapped[Optional["Dataset"]] = relationship(back_populates="hashes")
    dict_collection_visible_keys = ["id", "hash_function", "hash_value", "extra_files_path"]
    dict_element_visible_keys = ["id", "hash_function", "hash_value", "extra_files_path"]

    def _serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            hash_function=self.hash_function,
            hash_value=self.hash_value,
            extra_files_path=self.extra_files_path,
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def copy(self) -> "DatasetHash":
        new_hash = DatasetHash()
        new_hash.hash_function = self.hash_function
        new_hash.hash_value = self.hash_value
        new_hash.extra_files_path = self.extra_files_path
        return new_hash

    @property
    def hash_func_name(self) -> HashFunctionNameEnum:
        as_str = self.hash_function
        assert as_str
        return HashFunctionNameEnum(self.hash_function)


DescribesHash = Union[DatasetSourceHash, DatasetHash]


def datatype_for_extension(extension, datatypes_registry=None) -> "Data":
    if extension is not None:
        extension = extension.lower()
    if datatypes_registry is None:
        datatypes_registry = _get_datatypes_registry()
    if not extension or extension == "auto" or extension == "_sniff_":
        extension = "data"
    ret = datatypes_registry.get_datatype_by_extension(extension)
    if ret is None:
        log.warning(f"Datatype class not found for extension '{extension}'")
        return datatypes_registry.get_datatype_by_extension("data")
    return ret


class DatasetInstance(RepresentById, UsesCreateAndUpdateTime, _HasTable):
    """A base class for all 'dataset instances', HDAs, LDDAs, etc"""

    states = Dataset.states
    _state: Optional[str]
    conversion_messages = Dataset.conversion_messages
    permitted_actions = Dataset.permitted_actions
    purged: bool
    creating_job_associations: List[Union[JobToOutputDatasetCollectionAssociation, JobToOutputDatasetAssociation]]
    copied_from_history_dataset_association: Optional["HistoryDatasetAssociation"]
    copied_from_library_dataset_dataset_association: Optional["LibraryDatasetDatasetAssociation"]
    dependent_jobs: List[JobToInputLibraryDatasetAssociation]
    implicitly_converted_datasets: List["ImplicitlyConvertedDatasetAssociation"]
    implicitly_converted_parent_datasets: List["ImplicitlyConvertedDatasetAssociation"]

    validated_states = DatasetValidatedState

    def __init__(
        self,
        id=None,
        hid=None,
        name=None,
        info=None,
        blurb=None,
        peek=None,
        tool_version=None,
        extension=None,
        dbkey=None,
        metadata=None,
        dataset=None,
        deleted=False,
        designation=None,
        parent_id=None,
        validated_state=DatasetValidatedState.UNKNOWN,
        validated_state_message=None,
        visible=True,
        create_dataset=False,
        sa_session=None,
        extended_metadata=None,
        flush=True,
        metadata_deferred=False,
        creating_job_id=None,
        copied_from_history_dataset_association=None,
        copied_from_library_dataset_dataset_association=None,
    ):
        self.name = name or "Unnamed dataset"
        self.id = id
        self.info = info
        self.blurb = blurb
        self.peek = peek
        self.tool_version = tool_version
        self.extension = extension
        self.designation = designation
        # set private variable to None here, since the attribute may be needed in by MetadataCollection.__init__
        self._metadata = None
        self.metadata = metadata or {}
        self.metadata_deferred = metadata_deferred
        self.extended_metadata = extended_metadata
        if (
            dbkey
        ):  # dbkey is stored in metadata, only set if non-zero, or else we could clobber one supplied by input 'metadata'
            self._metadata["dbkey"] = listify(dbkey)
        self.deleted = deleted
        self.visible = visible
        self.validated_state = validated_state
        self.validated_state_message = validated_state_message
        # Relationships
        if copied_from_history_dataset_association:
            self.copied_from_history_dataset_association_id = copied_from_history_dataset_association.id
        if copied_from_library_dataset_dataset_association:
            self.copied_from_library_dataset_dataset_association_id = copied_from_library_dataset_dataset_association.id
        if not dataset and create_dataset:
            # Had to pass the sqlalchemy session in order to create a new dataset
            dataset = Dataset(state=Dataset.states.NEW)
            dataset.job_id = creating_job_id
            if flush:
                sa_session.add(dataset)
                with transaction(sa_session):
                    sa_session.commit()
        elif dataset:
            add_object_to_object_session(self, dataset)
        self.dataset = dataset
        ensure_object_added_to_session(self, object_in_session=dataset)
        self.parent_id = parent_id

    @property
    def peek(self):
        return self._peek

    @peek.setter
    def peek(self, peek):
        self._peek = unicodify(peek, strip_null=True)

    @property
    def ext(self):
        return self.extension

    @property
    def has_deferred_data(self):
        return self.dataset.state == Dataset.states.DEFERRED

    @property
    def deferred_source_uri(self):
        if self.has_deferred_data and self.sources:
            # Assuming the first source is the deferred source
            return self.sources[0].source_uri
        return None

    @property
    def state(self):
        # self._state holds state that should only affect this particular dataset association, not the dataset state itself
        if self._state:
            return self._state
        return self.dataset.state

    @state.setter
    def state(self, state: Optional[DatasetState]):
        if state != self.state:
            if state in (DatasetState.FAILED_METADATA, DatasetState.SETTING_METADATA):
                self._state = state
            else:
                self.set_metadata_success_state()
                sa_session = object_session(self)
                if sa_session:
                    sa_session.add(self.dataset)
                self.dataset.state = state

    def set_metadata_success_state(self):
        self._state = None

    def get_object_store_id(self):
        return self.dataset.object_store_id

    object_store_id = property(get_object_store_id)

    def get_quota_source_label(self):
        return self.dataset.quota_source_label

    quota_source_label = property(get_quota_source_label)

    def set_skipped(self, object_store_populator: "ObjectStorePopulator") -> None:
        assert self.dataset
        object_store_populator.set_object_store_id(self)
        self.extension = "expression.json"
        self.state = self.states.OK
        self.blurb = "skipped"
        self.visible = False
        null = json.dumps(None)
        with open(self.dataset.get_file_name(), "w") as out:
            out.write(null)
        self.peek = null
        self.set_total_size()

    def get_file_name(self, sync_cache: bool = True) -> str:
        return self.dataset.get_file_name(sync_cache=sync_cache)

    def set_file_name(self, filename: str):
        return self.dataset.set_file_name(filename)

    def link_to(self, path):
        self.dataset.set_file_name(os.path.abspath(path))
        # Since we are not copying the file into Galaxy's managed
        # default file location, the dataset should never be purgable.
        self.dataset.purgable = False

    @property
    def extra_files_path(self):
        return self.dataset.extra_files_path

    def extra_files_path_exists(self):
        return self.dataset.extra_files_path_exists()

    @property
    def datatype(self) -> "Data":
        return datatype_for_extension(self.extension)

    def get_metadata(self):
        # using weakref to store parent (to prevent circ ref),
        #   does a Session.clear() cause parent to be invalidated, while still copying over this non-database attribute?
        if not hasattr(self, "_metadata_collection") or self._metadata_collection.parent != self:
            self._metadata_collection = galaxy.model.metadata.MetadataCollection(self)
        return self._metadata_collection

    @property
    def set_metadata_requires_flush(self):
        return self.metadata.requires_dataset_id

    def set_metadata(self, bunch):
        # Needs to accept a MetadataCollection, a bunch, or a dict
        self._metadata = self.metadata.make_dict_copy(bunch)

    metadata = property(get_metadata, set_metadata)

    @property
    def has_metadata_files(self):
        return len(self.metadata_file_types) > 0

    @property
    def metadata_file_types(self):
        meta_types = []
        for meta_type in self.metadata.spec.keys():
            if isinstance(self.metadata.spec[meta_type].param, galaxy.model.metadata.FileParameter):
                meta_types.append(meta_type)
        return meta_types

    def get_metadata_file_paths_and_extensions(self) -> List[Tuple[str, str]]:
        metadata = self.metadata
        metadata_files = []
        for metadata_name in self.metadata_file_types:
            file_ext = metadata.spec[metadata_name].file_ext
            metadata_file = metadata[metadata_name]
            if metadata_file:
                path = metadata_file.get_file_name()
                metadata_files.append((file_ext, path))
        return metadata_files

    # This provide backwards compatibility with using the old dbkey
    # field in the database.  That field now maps to "old_dbkey" (see mapping.py).

    def get_dbkey(self):
        dbkey = self.metadata.dbkey
        if not isinstance(dbkey, list):
            dbkey = [dbkey]
        if dbkey in [[None], []]:
            return "?"
        return dbkey[0]

    def set_dbkey(self, value):
        if "dbkey" in self.datatype.metadata_spec:
            if not isinstance(value, list):
                self.metadata.dbkey = [value]

    dbkey = property(get_dbkey, set_dbkey)

    def ok_to_edit_metadata(self):
        """
        Prevent modifying metadata when dataset is queued or running as input/output:
        return `False` if there exists an associated job with a non-terminal state.
        """

        def exists_clause(assoc_model):
            return (
                select(assoc_model.job_id)
                .join(Job)
                .where(assoc_model.dataset_id == self.id)
                .where(Job.state.not_in(Job.terminal_states))
                .exists()
            )

        stmt = select(
            or_(
                exists_clause(JobToInputDatasetAssociation),
                exists_clause(JobToOutputDatasetAssociation),
            )
        )
        return not object_session(self).scalar(stmt)

    def change_datatype(self, new_ext):
        self.clear_associated_files()
        _get_datatypes_registry().change_datatype(self, new_ext)

    def get_size(self, nice_size=False, calculate_size=True):
        """Returns the size of the data on disk"""
        if nice_size:
            return galaxy.util.nice_size(self.dataset.get_size(calculate_size=calculate_size))
        return self.dataset.get_size(calculate_size=calculate_size)

    def set_size(self, **kwds):
        """Sets and gets the size of the data on disk"""
        return self.dataset.set_size(**kwds)

    def get_total_size(self):
        return self.dataset.get_total_size()

    def set_total_size(self):
        return self.dataset.set_total_size()

    def has_data(self):
        """Detects whether there is any data"""
        return self.dataset.has_data()

    def get_created_from_basename(self):
        return self.dataset.created_from_basename

    def set_created_from_basename(self, created_from_basename):
        if self.dataset.created_from_basename is not None:
            raise Exception("Underlying dataset already has a created_from_basename set.")
        self.dataset.created_from_basename = created_from_basename

    created_from_basename = property(get_created_from_basename, set_created_from_basename)

    @property
    def sources(self):
        return self.dataset.sources

    @property
    def hashes(self):
        return self.dataset.hashes

    def get_mime(self):
        """Returns the mime type of the data"""
        try:
            return _get_datatypes_registry().get_mimetype_by_extension(self.extension.lower())
        except AttributeError:
            # extension is None
            return "data"

    def set_peek(self, line_count=None, **kwd):
        try:
            # Certain datatype's set_peek methods contain a line_count argument
            return self.datatype.set_peek(self, line_count=line_count, **kwd)
        except TypeError:
            # ... and others don't
            return self.datatype.set_peek(self, **kwd)
        except Exception:
            # Never fail peek setting, but do log exception so datatype logic can be fixed
            log.exception("Setting peek failed")

    def init_meta(self, copy_from=None):
        return self.datatype.init_meta(self, copy_from=copy_from)

    def set_meta(self, **kwd):
        self.clear_associated_files(metadata_safe=True)
        return self.datatype.set_meta(self, **kwd)

    def missing_meta(self, **kwd):
        return self.datatype.missing_meta(self, **kwd)

    def as_display_type(self, type, **kwd):
        return self.datatype.as_display_type(self, type, **kwd)

    def display_peek(self):
        try:
            return self.datatype.display_peek(self)
        except Exception:
            log.exception("Error occurred while generating dataset peek")
            return None

    def display_name(self):
        return self.datatype.display_name(self)

    def display_info(self):
        return self.datatype.display_info(self)

    def get_converted_files_by_type(self, file_type):
        for assoc in self.implicitly_converted_datasets:
            if not assoc.deleted and assoc.type == file_type:
                item = assoc.dataset or assoc.dataset_ldda
                if not item.deleted and item.state in Dataset.valid_input_states:
                    return item
        return None

    def get_converted_dataset_deps(self, trans, target_ext):
        """
        Returns dict of { "dependency" => HDA }
        """
        # List of string of dependencies
        try:
            depends_list = trans.app.datatypes_registry.converter_deps[self.extension][target_ext]
        except KeyError:
            depends_list = []
        return {dep: self.get_converted_dataset(trans, dep) for dep in depends_list}

    def get_converted_dataset(self, trans, target_ext, target_context=None, history=None):
        """
        Return converted dataset(s) if they exist, along with a dict of dependencies.
        If not converted yet, do so and return None (the first time). If unconvertible, raise exception.
        """
        # See if we can convert the dataset
        if target_ext not in self.get_converter_types():
            raise NoConverterException(f"Conversion from '{self.extension}' to '{target_ext}' not possible")
        # See if converted dataset already exists, either in metadata in conversions.
        converted_dataset = self.get_metadata_dataset(target_ext)
        if converted_dataset:
            return converted_dataset
        converted_dataset = self.get_converted_files_by_type(target_ext)
        if converted_dataset:
            return converted_dataset
        deps = {}
        # List of string of dependencies
        try:
            depends_list = trans.app.datatypes_registry.converter_deps[self.extension][target_ext]
        except KeyError:
            depends_list = []
        # Conversion is possible but hasn't been done yet, run converter.
        # Check if we have dependencies
        try:
            for dependency in depends_list:
                dep_dataset = self.get_converted_dataset(trans, dependency)
                if dep_dataset is None:
                    # None means converter is running first time
                    return None
                elif dep_dataset.state == Job.states.ERROR:
                    raise ConverterDependencyException(f"A dependency ({dependency}) was in an error state.")
                elif dep_dataset.state != Job.states.OK:
                    # Pending
                    return None
                deps[dependency] = dep_dataset
        except NoConverterException:
            raise NoConverterException(f"A dependency ({dependency}) is missing a converter.")
        except KeyError:
            pass  # No deps
        return next(
            iter(
                self.datatype.convert_dataset(
                    trans,
                    self,
                    target_ext,
                    return_output=True,
                    visible=False,
                    deps=deps,
                    target_context=target_context,
                    history=history,
                ).values()
            )
        )

    def attach_implicitly_converted_dataset(self, session, new_dataset, target_ext: str):
        new_dataset.name = self.name
        self.copy_attributes(new_dataset)
        assoc = ImplicitlyConvertedDatasetAssociation(
            parent=self, file_type=target_ext, dataset=new_dataset, metadata_safe=False
        )
        session.add(new_dataset)
        session.add(assoc)

    def copy_attributes(self, new_dataset):
        """
        Copies attributes to a new datasets, used for implicit conversions
        """

    def get_metadata_dataset(self, dataset_ext):
        """
        Returns an HDA that points to a metadata file which contains a
        converted data with the requested extension.
        """
        for name, value in self.metadata.items():
            # HACK: MetadataFile objects do not have a type/ext, so need to use metadata name
            # to determine type.
            if dataset_ext == "bai" and name == "bam_index" and isinstance(value, MetadataFile):
                # HACK: MetadataFile objects cannot be used by tools, so return
                # a fake HDA that points to metadata file.
                fake_dataset = Dataset(state=Dataset.states.OK, external_filename=value.get_file_name())
                fake_hda = HistoryDatasetAssociation(dataset=fake_dataset)
                return fake_hda

    def clear_associated_files(self, metadata_safe=False, purge=False):
        raise Exception("Unimplemented")

    def get_converter_types(self):
        return self.datatype.get_converter_types(self, _get_datatypes_registry())

    def can_convert_to(self, format):
        return format in self.get_converter_types()

    def find_conversion_destination(
        self, accepted_formats: List[str], **kwd
    ) -> Tuple[bool, Optional[str], Optional["DatasetInstance"]]:
        """Returns ( target_ext, existing converted dataset )"""
        return self.datatype.find_conversion_destination(self, accepted_formats, _get_datatypes_registry(), **kwd)

    def add_validation_error(self, validation_error):
        self.validation_errors.append(validation_error)

    def extend_validation_errors(self, validation_errors):
        self.validation_errors.extend(validation_errors)

    def mark_deleted(self):
        self.deleted = True

    def mark_undeleted(self):
        self.deleted = False

    def mark_unhidden(self):
        self.visible = True

    def undeletable(self):
        if self.purged:
            return False
        return True

    @property
    def is_ok(self):
        return self.state == self.states.OK

    @property
    def is_pending(self):
        """
        Return true if the dataset is neither ready nor in error
        """
        return self.state in (
            self.states.NEW,
            self.states.UPLOAD,
            self.states.QUEUED,
            self.states.RUNNING,
            self.states.SETTING_METADATA,
        )

    @property
    def source_library_dataset(self):
        def get_source(dataset):
            if isinstance(dataset, LibraryDatasetDatasetAssociation):
                if dataset.library_dataset:
                    return (dataset, dataset.library_dataset)
            if dataset.copied_from_library_dataset_dataset_association:
                source = get_source(dataset.copied_from_library_dataset_dataset_association)
                if source:
                    return source
            if dataset.copied_from_history_dataset_association:
                source = get_source(dataset.copied_from_history_dataset_association)
                if source:
                    return source
            return (None, None)

        return get_source(self)

    @property
    def source_dataset_chain(self):
        def _source_dataset_chain(dataset, lst):
            try:
                cp_from_ldda = dataset.copied_from_library_dataset_dataset_association
                if cp_from_ldda:
                    lst.append((cp_from_ldda, "(Data Library)"))
                    return _source_dataset_chain(cp_from_ldda, lst)
            except Exception as e:
                log.warning(e)
            try:
                cp_from_hda = dataset.copied_from_history_dataset_association
                if cp_from_hda:
                    lst.append((cp_from_hda, cp_from_hda.history.name))
                    return _source_dataset_chain(cp_from_hda, lst)
            except Exception as e:
                log.warning(e)
            return lst

        return _source_dataset_chain(self, [])

    @property
    def creating_job(self) -> Optional[Job]:
        # TODO this should work with `return self.dataset.job` (revise failing unit tests)
        creating_job_associations = None
        if self.creating_job_associations:
            creating_job_associations = self.creating_job_associations
        else:
            inherit_chain = self.source_dataset_chain
            if inherit_chain:
                creating_job_associations = inherit_chain[-1][0].creating_job_associations
        if creating_job_associations:
            return creating_job_associations[0].job
        return None

    def get_display_applications(self, trans):
        return self.datatype.get_display_applications_by_dataset(self, trans)

    def get_datasources(self, trans):
        """
        Returns datasources for dataset; if datasources are not available
        due to indexing, indexing is started. Return value is a dictionary
        with entries of type
        (<datasource_type> : {<datasource_name>, <indexing_message>}).
        """
        data_sources_dict = {}
        msg = None
        for source_type, source_list in self.datatype.data_sources.items():
            data_source = None
            if source_type == "data_standalone":
                # Nothing to do.
                msg = None
                data_source = source_list
            else:
                # Convert.
                if isinstance(source_list, str):
                    source_list = [source_list]

                # Loop through sources until viable one is found.
                for source in source_list:
                    msg = self.convert_dataset(trans, source)
                    # No message or PENDING means that source is viable. No
                    # message indicates conversion was done and is successful.
                    if not msg or msg == self.conversion_messages.PENDING:
                        data_source = source
                        break

            # Store msg.
            data_sources_dict[source_type] = {"name": data_source, "message": msg}

        return data_sources_dict

    def convert_dataset(self, trans, target_type):
        """
        Converts a dataset to the target_type and returns a message indicating
        status of the conversion. None is returned to indicate that dataset
        was converted successfully.
        """

        # Get converted dataset; this will start the conversion if necessary.
        try:
            converted_dataset = self.get_converted_dataset(trans, target_type)
        except NoConverterException:
            return self.conversion_messages.NO_CONVERTER
        except ConverterDependencyException as dep_error:
            return {"kind": self.conversion_messages.ERROR, "message": dep_error.value}

        # Check dataset state and return any messages.
        msg = None
        if converted_dataset and converted_dataset.state == Dataset.states.ERROR:
            stmt = select(JobToOutputDatasetAssociation.job_id).filter_by(dataset_id=converted_dataset.id).limit(1)
            job_id = trans.sa_session.scalars(stmt).first()
            job = trans.sa_session.get(Job, job_id)
            msg = {"kind": self.conversion_messages.ERROR, "message": job.stderr}
        elif not converted_dataset or converted_dataset.state != Dataset.states.OK:
            msg = self.conversion_messages.PENDING

        return msg

    def _serialize(self, id_encoder, serialization_options):
        metadata = _prepare_metadata_for_serialization(id_encoder, serialization_options, self.metadata)
        rval = dict_for(
            self,
            create_time=self.create_time.__str__(),
            update_time=self.update_time.__str__(),
            name=unicodify(self.name),
            info=unicodify(self.info),
            blurb=self.blurb,
            peek=self.peek,
            extension=self.extension,
            metadata=metadata,
            designation=self.designation,
            deleted=self.deleted,
            visible=self.visible,
            dataset_uuid=(lambda uuid: str(uuid) if uuid else None)(self.dataset.uuid),
            validated_state=self.validated_state,
            validated_state_message=self.validated_state_message,
        )

        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def _handle_serialize_files(self, id_encoder, serialization_options, rval):
        if serialization_options.serialize_dataset_objects:
            rval["dataset"] = self.dataset.serialize(id_encoder, serialization_options)
        else:
            serialization_options.serialize_files(self, rval)
            file_metadata = {}
            dataset = self.dataset
            hashes = dataset.hashes
            if hashes:
                file_metadata["hashes"] = [h.serialize(id_encoder, serialization_options) for h in hashes]
            if dataset.created_from_basename is not None:
                file_metadata["created_from_basename"] = dataset.created_from_basename
            sources = dataset.sources
            if sources:
                file_metadata["sources"] = [s.serialize(id_encoder, serialization_options) for s in sources]

            rval["file_metadata"] = file_metadata


class HistoryDatasetAssociation(DatasetInstance, HasTags, Dictifiable, UsesAnnotations, HasName, Serializable):
    """
    Resource class that creates a relation between a dataset and a user history.
    """

    history_id: Optional[int]

    def __init__(
        self,
        hid=None,
        history=None,
        sa_session=None,
        **kwd,
    ):
        """
        Create a a new HDA and associate it with the given history.
        """
        # FIXME: sa_session is must be passed to DataSetInstance if the create_dataset
        # parameter is True so that the new object can be flushed.  Is there a better way?
        DatasetInstance.__init__(self, sa_session=sa_session, **kwd)
        self.hid = hid
        # Relationships
        self.history = history

    def __strict_check_before_flush__(self):
        if self.extension != "len":
            # TODO: Custom builds (with .len extension) do not get a history or a HID.
            # These should get some other type of permanent storage, perhaps UserDatasetAssociation ?
            # Everything else needs to have a hid and a history
            if not self.history and not getattr(self, "history_id", None):
                raise Exception(f"HistoryDatasetAssociation {self} without history detected, this is not valid")
            elif not self.hid:
                raise Exception(f"HistoryDatasetAssociation {self} without hid, this is not valid")
            elif self.dataset.file_size is None and self.dataset.state not in self.dataset.no_data_states:
                raise Exception(
                    f"HistoryDatasetAssociation {self} in state {self.dataset.state} with null file size, this is not valid"
                )

    @property
    def user(self):
        if self.history:
            return self.history.user

    def __create_version__(self, session):
        state = inspect(self)
        changes = {}

        for attr in state.mapper.columns:
            # We only create a new version if columns of the HDA table have changed, and ignore relationships.
            hist = state.get_history(attr.key, True)

            if not hist.has_changes():
                continue

            # hist.deleted holds old value(s)
            changes[attr.key] = hist.deleted
        if changes and self.update_time and self.state == self.states.OK and not self.deleted:
            # We only record changes to HDAs that exist in the database and have a update_time
            new_values = {}
            new_values["name"] = changes.get("name", self.name)
            new_values["dbkey"] = changes.get("dbkey", self.dbkey)
            new_values["extension"] = changes.get("extension", self.extension)
            new_values["extended_metadata_id"] = changes.get("extended_metadata_id", self.extended_metadata_id)
            for k, v in new_values.items():
                if isinstance(v, list):
                    new_values[k] = v[0]
            new_values["update_time"] = self.update_time
            new_values["version"] = self.version or 1
            new_values["metadata"] = self._metadata
            past_hda = HistoryDatasetAssociationHistory(history_dataset_association_id=self.id, **new_values)
            self.version = self.version + 1 if self.version else 1
            session.add(past_hda)

    def copy_from(self, other_hda, new_dataset=None, include_tags=True, include_metadata=False):
        # This deletes the old dataset, so make sure to only call this on new things
        # in the history (e.g. during job finishing).
        old_dataset = self.dataset
        if include_metadata:
            self._metadata = other_hda._metadata
        self.metadata_deferred = other_hda.metadata_deferred
        self.info = other_hda.info
        self.blurb = other_hda.blurb
        self.peek = other_hda.peek
        self.extension = other_hda.extension
        self.designation = other_hda.designation
        self.deleted = other_hda.deleted
        self.visible = other_hda.visible
        self.validated_state = other_hda.validated_state
        self.validated_state_message = other_hda.validated_state_message
        if include_tags and self.history:
            self.copy_tags_from(self.user, other_hda)
        self.dataset = new_dataset or other_hda.dataset
        self.copied_from_history_dataset_association_id = other_hda.id
        if old_dataset:
            old_dataset.full_delete()

    def copy(self, parent_id=None, copy_tags=None, flush=True, copy_hid=True, new_name=None):
        """
        Create a copy of this HDA.
        """
        hid = None
        if copy_hid:
            hid = self.hid
        hda = HistoryDatasetAssociation(
            hid=hid,
            name=new_name or self.name,
            info=self.info,
            blurb=self.blurb,
            peek=self.peek,
            tool_version=self.tool_version,
            extension=self.extension,
            dbkey=self.dbkey,
            dataset=self.dataset,
            visible=self.visible,
            deleted=self.deleted,
            parent_id=parent_id,
            copied_from_history_dataset_association=self,
            flush=False,
        )
        # update init non-keywords as well
        hda.purged = self.purged

        hda.copy_tags_to(copy_tags)
        object_session(self).add(hda)
        hda.metadata = self.metadata
        if flush:
            session = object_session(self)
            with transaction(session):
                session.commit()
        return hda

    def copy_tags_to(self, copy_tags=None):
        if copy_tags is not None:
            if isinstance(copy_tags, dict):
                copy_tags = copy_tags.values()
            for tag in copy_tags:
                copied_tag = tag.copy(cls=HistoryDatasetAssociationTagAssociation)
                self.tags.append(copied_tag)

    def copy_attributes(self, new_dataset):
        if new_dataset.hid is None:
            new_dataset.hid = self.hid

    def to_library_dataset_dataset_association(
        self,
        trans,
        target_folder,
        replace_dataset=None,
        parent_id=None,
        roles=None,
        ldda_message="",
        element_identifier=None,
    ) -> "LibraryDatasetDatasetAssociation":
        """
        Copy this HDA to a library optionally replacing an existing LDDA.
        """
        if not self.dataset.shareable:
            raise Exception("Attempting to share a non-shareable dataset.")

        if replace_dataset:
            # The replace_dataset param ( when not None ) refers to a LibraryDataset that
            #   is being replaced with a new version.
            library_dataset = replace_dataset
        else:
            # If replace_dataset is None, the Library level permissions will be taken from the folder and
            #   applied to the new LibraryDataset, and the current user's DefaultUserPermissions will be applied
            #   to the associated Dataset.
            library_dataset = LibraryDataset(folder=target_folder, name=self.name, info=self.info)
        user = trans.user or self.history.user
        ldda = LibraryDatasetDatasetAssociation(
            name=element_identifier or self.name,
            info=self.info,
            blurb=self.blurb,
            peek=self.peek,
            tool_version=self.tool_version,
            extension=self.extension,
            dbkey=self.dbkey,
            dataset=self.dataset,
            library_dataset=library_dataset,
            visible=self.visible,
            deleted=self.deleted,
            parent_id=parent_id,
            copied_from_history_dataset_association=self,
            user=user,
        )
        library_dataset.library_dataset_dataset_association = ldda
        session = object_session(self)
        assert session
        session.add(library_dataset)
        # If roles were selected on the upload form, restrict access to the Dataset to those roles
        roles = roles or []
        for role in roles:
            dp = trans.model.DatasetPermissions(
                trans.app.security_agent.permitted_actions.DATASET_ACCESS.action, ldda.dataset, role
            )
            trans.sa_session.add(dp)
        # Must set metadata after ldda flushed, as MetadataFiles require ldda.id
        if self.set_metadata_requires_flush:
            with transaction(session):
                session.commit()
        ldda.metadata = self.metadata
        # TODO: copy #tags from history
        if ldda_message:
            ldda.message = ldda_message
        if not replace_dataset:
            target_folder.add_library_dataset(library_dataset, genome_build=ldda.dbkey)
            session.add(target_folder)
        session.add(library_dataset)

        with transaction(session):
            session.commit()

        return ldda

    def clear_associated_files(self, metadata_safe=False, purge=False):
        """ """
        # metadata_safe = True means to only clear when assoc.metadata_safe == False
        for assoc in self.implicitly_converted_datasets:
            if not assoc.deleted and (not metadata_safe or not assoc.metadata_safe):
                assoc.clear(purge=purge)
        for assoc in self.implicitly_converted_parent_datasets:
            assoc.clear(purge=purge, delete_dataset=False)

    def get_access_roles(self, security_agent):
        """
        Return The access roles associated with this HDA's dataset.
        """
        return self.dataset.get_access_roles(security_agent)

    def purge_usage_from_quota(self, user, quota_source_info):
        """Remove this HDA's quota_amount from user's quota."""
        if user and quota_source_info.use:
            user.adjust_total_disk_usage(-self.quota_amount(user), quota_source_info.label)

    def quota_amount(self, user):
        """
        Return the disk space used for this HDA relevant to user quotas.

        If the user has multiple instances of this dataset, it will not affect their
        disk usage statistic.
        """
        rval = 0
        # Anon users are handled just by their single history size.
        if not user:
            return rval
        # Gets an HDA disk usage, if the user does not already
        #   have an association of the same dataset
        if not self.dataset.library_associations and not self.purged and not self.dataset.purged:
            for hda in self.dataset.history_associations:
                if hda.id == self.id:
                    continue
                if not hda.purged and hda.history and hda.user and hda.user == user:
                    break
            else:
                rval += self.get_total_size()
        return rval

    def _serialize(self, id_encoder, serialization_options):
        rval = super()._serialize(id_encoder, serialization_options)
        rval["state"] = self.state
        rval["hid"] = self.hid
        rval["annotation"] = unicodify(getattr(self, "annotation", ""))
        rval["tags"] = self.make_tag_string_list()
        rval["tool_version"] = self.tool_version
        if self.history:
            rval["history_encoded_id"] = serialization_options.get_identifier(id_encoder, self.history)

        # Handle copied_from_history_dataset_association information...
        copied_from_history_dataset_association_chain = []
        src_hda = self
        while src_hda.copied_from_history_dataset_association:
            src_hda = src_hda.copied_from_history_dataset_association
            copied_from_history_dataset_association_chain.append(
                serialization_options.get_identifier(id_encoder, src_hda)
            )
        rval["copied_from_history_dataset_association_id_chain"] = copied_from_history_dataset_association_chain
        self._handle_serialize_files(id_encoder, serialization_options, rval)
        return rval

    def to_dict(self, view="collection", expose_dataset_path=False):
        """
        Return attributes of this HDA that are exposed using the API.
        """
        # Since this class is a proxy to rather complex attributes we want to
        # display in other objects, we can't use the simpler method used by
        # other model classes.
        original_rval = super().to_dict(view=view)
        hda = self
        rval = dict(
            id=hda.id,
            hda_ldda="hda",
            uuid=(lambda uuid: str(uuid) if uuid else None)(hda.dataset.uuid),
            hid=hda.hid,
            file_ext=hda.ext,
            peek=unicodify(hda.display_peek()) if hda.peek and hda.peek != "no peek" else None,
            model_class=self.__class__.__name__,
            name=hda.name,
            deleted=hda.deleted,
            purged=hda.purged,
            visible=hda.visible,
            state=hda.state,
            history_content_type=hda.history_content_type,
            file_size=int(hda.get_size()),
            create_time=hda.create_time.isoformat(),
            update_time=hda.update_time.isoformat(),
            data_type=f"{hda.datatype.__class__.__module__}.{hda.datatype.__class__.__name__}",
            genome_build=hda.dbkey,
            validated_state=hda.validated_state,
            validated_state_message=hda.validated_state_message,
            misc_info=hda.info.strip() if isinstance(hda.info, str) else hda.info,
            misc_blurb=hda.blurb,
        )

        rval.update(original_rval)

        if hda.copied_from_library_dataset_dataset_association is not None:
            rval["copied_from_ldda_id"] = hda.copied_from_library_dataset_dataset_association.id

        if hda.history is not None:
            rval["history_id"] = hda.history.id

        if hda.extended_metadata is not None:
            rval["extended_metadata"] = hda.extended_metadata.data

        for name in hda.metadata.spec.keys():
            val = hda.metadata.get(name)
            if isinstance(val, MetadataFile):
                # only when explicitly set: fetching filepaths can be expensive
                if not expose_dataset_path:
                    continue
                val = val.get_file_name()
            # If no value for metadata, look in datatype for metadata.
            elif not hda.metadata.element_is_set(name) and hasattr(hda.datatype, name):
                val = getattr(hda.datatype, name)
            rval[f"metadata_{name}"] = val
        return rval

    def unpause_dependent_jobs(self, jobs=None):
        if self.state == self.states.PAUSED:
            self.state = self.states.NEW
            self.info = None
        jobs_to_unpause = jobs or set()
        for jtida in self.dependent_jobs:
            if jtida.job not in jobs_to_unpause:
                jobs_to_unpause.add(jtida.job)
                for jtoda in jtida.job.output_datasets:
                    jobs_to_unpause.update(jtoda.dataset.unpause_dependent_jobs(jobs=jobs_to_unpause))
        return jobs_to_unpause

    @property
    def history_content_type(self):
        return "dataset"

    # TODO: down into DatasetInstance
    content_type = "dataset"

    @hybrid.hybrid_property
    def type_id(self):
        return "-".join((self.content_type, str(self.id)))

    @type_id.expression  # type: ignore[no-redef]
    def type_id(cls):
        return (type_coerce(cls.content_type, Unicode) + "-" + type_coerce(cls.id, Unicode)).label("type_id")


class HistoryDatasetAssociationHistory(Base):
    __tablename__ = "history_dataset_association_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    history_dataset_association_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("history_dataset_association.id"), index=True
    )
    update_time: Mapped[Optional[datetime]] = mapped_column(default=now)
    version: Mapped[Optional[int]]
    name: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    extension: Mapped[Optional[str]] = mapped_column(TrimmedString(64))
    _metadata = Column("metadata", MetadataType)
    extended_metadata_id: Mapped[Optional[int]] = mapped_column(ForeignKey("extended_metadata.id"), index=True)

    def __init__(
        self,
        history_dataset_association_id,
        name,
        dbkey,
        update_time,
        version,
        extension,
        extended_metadata_id,
        metadata,
    ):
        self.history_dataset_association_id = history_dataset_association_id
        self.name = name
        self.dbkey = dbkey
        self.update_time = update_time
        self.version = version
        self.extension = extension
        self.extended_metadata_id = extended_metadata_id
        self._metadata = metadata


# hda read access permission given by a user to a specific site (gen. for external display applications)
class HistoryDatasetAssociationDisplayAtAuthorization(Base, RepresentById):
    __tablename__ = "history_dataset_association_display_at_authorization"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(index=True, default=now, onupdate=now, nullable=True)
    history_dataset_association_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("history_dataset_association.id"), index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    site: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    history_dataset_association: Mapped[Optional["HistoryDatasetAssociation"]] = relationship()
    user: Mapped[Optional["User"]] = relationship()

    def __init__(self, hda=None, user=None, site=None):
        self.history_dataset_association = hda
        self.user = user
        self.site = site


class HistoryDatasetAssociationSubset(Base, RepresentById):
    __tablename__ = "history_dataset_association_subset"

    id: Mapped[int] = mapped_column(primary_key=True)
    history_dataset_association_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("history_dataset_association.id"), index=True
    )
    history_dataset_association_subset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("history_dataset_association.id"), index=True
    )
    location: Mapped[Optional[str]] = mapped_column(Unicode(255), index=True)

    hda: Mapped[Optional["HistoryDatasetAssociation"]] = relationship(
        primaryjoin=(
            lambda: HistoryDatasetAssociationSubset.history_dataset_association_id == HistoryDatasetAssociation.id
        ),
    )
    subset: Mapped[Optional["HistoryDatasetAssociation"]] = relationship(
        primaryjoin=(
            lambda: HistoryDatasetAssociationSubset.history_dataset_association_subset_id
            == HistoryDatasetAssociation.id
        ),
    )

    def __init__(self, hda, subset, location):
        self.hda = hda
        self.subset = subset
        self.location = location


class Library(Base, Dictifiable, HasName, Serializable):
    __tablename__ = "library"

    id: Mapped[int] = mapped_column(primary_key=True)
    root_folder_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library_folder.id"), index=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    purged: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    description: Mapped[Optional[str]] = mapped_column(TEXT)
    synopsis: Mapped[Optional[str]] = mapped_column(TEXT)
    root_folder = relationship("LibraryFolder", back_populates="library_root")
    actions: Mapped[List["LibraryPermissions"]] = relationship(back_populates="library")

    permitted_actions = get_permitted_actions(filter="LIBRARY")
    dict_collection_visible_keys = ["id", "name"]
    dict_element_visible_keys = ["id", "deleted", "name", "description", "synopsis", "root_folder_id", "create_time"]

    def __init__(self, name=None, description=None, synopsis=None, root_folder=None):
        self.name = name or "Unnamed library"
        self.description = description
        self.synopsis = synopsis
        self.root_folder = root_folder

    def _serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            name=self.name,
            description=self.description,
            synopsis=self.synopsis,
        )
        if self.root_folder:
            rval["root_folder"] = self.root_folder.serialize(id_encoder, serialization_options)

        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def to_dict(self, view="collection", value_mapper=None):
        """
        We prepend an F to folders.
        """
        rval = super().to_dict(view=view, value_mapper=value_mapper)
        return rval

    def get_active_folders(self, folder, folders=None):
        # TODO: should we make sure the library is not deleted?
        def sort_by_attr(seq, attr):
            """
            Sort the sequence of objects by object's attribute
            Arguments:
            seq  - the list or any sequence (including immutable one) of objects to sort.
            attr - the name of attribute to sort by
            """
            # Use the "Schwartzian transform"
            # Create the auxiliary list of tuples where every i-th tuple has form
            # (seq[i].attr, i, seq[i]) and sort it. The second item of tuple is needed not
            # only to provide stable sorting, but mainly to eliminate comparison of objects
            # (which can be expensive or prohibited) in case of equal attribute values.
            intermed = [(getattr(v, attr), i, v) for i, v in enumerate(seq)]
            intermed.sort()
            return [_[-1] for _ in intermed]

        if folders is None:
            active_folders = [folder]
        for active_folder in folder.active_folders:
            active_folders.extend(self.get_active_folders(active_folder, folders))
        return sort_by_attr(active_folders, "id")

    def get_access_roles(self, security_agent):
        roles = []
        for lp in self.actions:
            if lp.action == security_agent.permitted_actions.LIBRARY_ACCESS.action:
                roles.append(lp.role)
        return roles


class LibraryFolder(Base, Dictifiable, HasName, Serializable):
    __tablename__ = "library_folder"
    __table_args__ = (Index("ix_library_folder_name", "name", mysql_length=200),)

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library_folder.id"), index=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(TEXT)
    description: Mapped[Optional[str]] = mapped_column(TEXT)
    order_id: Mapped[Optional[int]]  # not currently being used, but for possible future use
    item_count: Mapped[Optional[int]]
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    purged: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    genome_build: Mapped[Optional[str]] = mapped_column(TrimmedString(40))

    folders: Mapped[List["LibraryFolder"]] = relationship(
        primaryjoin=(lambda: LibraryFolder.id == LibraryFolder.parent_id),
        order_by=asc(name),
        back_populates="parent",
    )
    parent: Mapped[Optional["LibraryFolder"]] = relationship(back_populates="folders", remote_side=[id])

    active_folders: Mapped[List["LibraryFolder"]] = relationship(
        primaryjoin=("and_(LibraryFolder.parent_id == LibraryFolder.id, not_(LibraryFolder.deleted))"),
        order_by=asc(name),
        # """sqlalchemy.exc.ArgumentError: Error creating eager relationship 'active_folders'
        # on parent class '<class 'galaxy.model.LibraryFolder'>' to child class '<class 'galaxy.model.LibraryFolder'>':
        # Cant use eager loading on a self referential relationship."""
        # TODO: This is no longer the case. Fix this: https://docs.sqlalchemy.org/en/14/orm/self_referential.html#configuring-self-referential-eager-loading
        viewonly=True,
    )

    datasets: Mapped[List["LibraryDataset"]] = relationship(
        primaryjoin=(
            lambda: LibraryDataset.folder_id == LibraryFolder.id
            and LibraryDataset.library_dataset_dataset_association_id.isnot(None)
        ),
        order_by=(lambda: asc(LibraryDataset._name)),
        viewonly=True,
    )

    active_datasets: Mapped[List["LibraryDataset"]] = relationship(
        primaryjoin=(
            "and_(LibraryDataset.folder_id == LibraryFolder.id, not_(LibraryDataset.deleted), LibraryDataset.library_dataset_dataset_association_id.isnot(None))"
        ),
        order_by=(lambda: asc(LibraryDataset._name)),
        viewonly=True,
    )

    library_root = relationship("Library", back_populates="root_folder")
    actions: Mapped[List["LibraryFolderPermissions"]] = relationship(back_populates="folder")

    dict_element_visible_keys = [
        "id",
        "parent_id",
        "name",
        "description",
        "item_count",
        "genome_build",
        "update_time",
        "deleted",
    ]

    def __init__(self, name=None, description=None, item_count=0, order_id=None, genome_build=None):
        self.name = name or "Unnamed folder"
        self.description = description
        self.item_count = item_count
        self.order_id = order_id
        self.genome_build = genome_build

    def add_library_dataset(self, library_dataset, genome_build=None):
        library_dataset.folder_id = self.id
        library_dataset.order_id = self.item_count
        self.item_count += 1
        if genome_build not in [None, "?"]:
            self.genome_build = genome_build

    def add_folder(self, folder):
        folder.parent_id = self.id
        folder.order_id = self.item_count
        self.item_count += 1

    @property
    def activatable_library_datasets(self):
        # This needs to be a list
        return [
            ld
            for ld in self.datasets
            if ld.library_dataset_dataset_association and not ld.library_dataset_dataset_association.dataset.deleted
        ]

    def _serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            id=self.id,  # FIXME: serialize only in sessionless export mode
            name=self.name,
            description=self.description,
            genome_build=self.genome_build,
            item_count=self.item_count,
            order_id=self.order_id,
            # update_time=self.update_time,
            deleted=self.deleted,
        )
        folders = []
        for folder in self.folders:
            folders.append(folder.serialize(id_encoder, serialization_options))
        rval["folders"] = folders
        datasets = []
        for dataset in self.datasets:
            datasets.append(dataset.serialize(id_encoder, serialization_options))
        rval["datasets"] = datasets
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def to_dict(self, view="collection", value_mapper=None):
        rval = super().to_dict(view=view, value_mapper=value_mapper)
        rval["library_path"] = self.library_path
        rval["parent_library_id"] = self.parent_library.id
        return rval

    @property
    def library_path(self):
        l_path = []
        f = self
        while f.parent:
            l_path.insert(0, f.name)
            f = f.parent
        return l_path

    @property
    def parent_library(self):
        f = self
        while f.parent:
            f = f.parent
        return f.library_root[0]


class LibraryDataset(Base, Serializable):
    __tablename__ = "library_dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    # current version of dataset, if null, there is not a current version selected
    library_dataset_dataset_association_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(
            "library_dataset_dataset_association.id", use_alter=True, name="library_dataset_dataset_association_id_fk"
        ),
        index=True,
    )
    folder_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library_folder.id"), index=True)
    # not currently being used, but for possible future use
    order_id: Mapped[Optional[int]]
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    # when not None/null this will supercede display in library (but not when imported into user's history?)
    _name: Mapped[Optional[str]] = mapped_column("name", TrimmedString(255), index=True)
    # when not None/null this will supercede display in library (but not when imported into user's history?)
    _info: Mapped[Optional[str]] = mapped_column("info", TrimmedString(255))
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    purged: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    folder: Mapped[Optional["LibraryFolder"]] = relationship()
    library_dataset_dataset_association = relationship(
        "LibraryDatasetDatasetAssociation", foreign_keys=library_dataset_dataset_association_id, post_update=True
    )
    expired_datasets: Mapped[List["LibraryDatasetDatasetAssociation"]] = relationship(
        foreign_keys=[id, library_dataset_dataset_association_id],
        primaryjoin=(
            "and_(LibraryDataset.id == LibraryDatasetDatasetAssociation.library_dataset_id, \
             not_(LibraryDataset.library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.id))"
        ),
        viewonly=True,
        uselist=True,
    )
    actions: Mapped[List["LibraryDatasetPermissions"]] = relationship(back_populates="library_dataset")

    # This class acts as a proxy to the currently selected LDDA
    upload_options = [
        ("upload_file", "Upload files"),
        ("upload_directory", "Upload directory of files"),
        ("upload_paths", "Upload files from filesystem paths"),
        ("import_from_history", "Import datasets from your current history"),
    ]

    def get_info(self):
        if self.library_dataset_dataset_association:
            return self.library_dataset_dataset_association.info
        elif self._info:
            return self._info
        else:
            return "no info"

    def set_info(self, info):
        self._info = info

    info = property(get_info, set_info)

    def get_name(self):
        if self.library_dataset_dataset_association:
            return self.library_dataset_dataset_association.name
        elif self._name:
            return self._name
        else:
            return "Unnamed dataset"

    def set_name(self, name):
        self._name = name

    name = property(get_name, set_name)

    def display_name(self):
        self.library_dataset_dataset_association.display_name()

    def _serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            name=self.name,
            info=self.info,
            order_id=self.order_id,
            ldda=self.library_dataset_dataset_association.serialize(id_encoder, serialization_options, for_link=True),
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def to_dict(self, view="collection"):
        # Since this class is a proxy to rather complex attributes we want to
        # display in other objects, we can't use the simpler method used by
        # other model classes.
        ldda = self.library_dataset_dataset_association
        rval = dict(
            id=self.id,
            ldda_id=ldda.id,
            parent_library_id=self.folder.parent_library.id,
            folder_id=self.folder_id,
            model_class=self.__class__.__name__,
            state=ldda.state,
            name=ldda.name,
            file_name=ldda.get_file_name(),
            created_from_basename=ldda.created_from_basename,
            uploaded_by=ldda.user and ldda.user.email,
            message=ldda.message,
            date_uploaded=ldda.create_time.isoformat(),
            update_time=ldda.update_time.isoformat(),
            file_size=int(ldda.get_size()),
            file_ext=ldda.ext,
            data_type=f"{ldda.datatype.__class__.__module__}.{ldda.datatype.__class__.__name__}",
            genome_build=ldda.dbkey,
            misc_info=ldda.info,
            misc_blurb=ldda.blurb,
            peek=(lambda ldda: ldda.display_peek() if ldda.peek and ldda.peek != "no peek" else None)(ldda),
        )
        if ldda.dataset.uuid is None:
            rval["uuid"] = None
        else:
            rval["uuid"] = str(ldda.dataset.uuid)
        for name in ldda.metadata.spec.keys():
            val = ldda.metadata.get(name)
            if isinstance(val, MetadataFile):
                val = val.get_file_name()
            elif isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            rval[f"metadata_{name}"] = val
        return rval


class LibraryDatasetDatasetAssociation(DatasetInstance, HasName, Serializable):
    message: Mapped[Optional[str]]
    tags: Mapped[List["LibraryDatasetDatasetAssociationTagAssociation"]]

    def __init__(
        self,
        library_dataset=None,
        user=None,
        sa_session=None,
        **kwd,
    ):
        # FIXME: sa_session is must be passed to DataSetInstance if the create_dataset
        # parameter in kwd is True so that the new object can be flushed.  Is there a better way?
        DatasetInstance.__init__(self, sa_session=sa_session, **kwd)
        self.library_dataset = library_dataset
        self.user = user

    def to_history_dataset_association(
        self, target_history, parent_id=None, add_to_history=False, visible=None, commit=True
    ):
        sa_session = object_session(self)
        hda = HistoryDatasetAssociation(
            name=self.name,
            info=self.info,
            blurb=self.blurb,
            peek=self.peek,
            tool_version=self.tool_version,
            extension=self.extension,
            dbkey=self.dbkey,
            dataset=self.dataset,
            visible=visible if visible is not None else self.visible,
            deleted=self.deleted,
            parent_id=parent_id,
            copied_from_library_dataset_dataset_association=self,
            history=target_history,
        )

        tag_manager = galaxy.model.tags.GalaxyTagHandler(sa_session)
        src_ldda_tags = tag_manager.get_tags_str(self.tags)
        tag_manager.apply_item_tags(user=self.user, item=hda, tags_str=src_ldda_tags, flush=False)
        sa_session.add(hda)
        hda.metadata = self.metadata
        if add_to_history and target_history:
            target_history.stage_addition(hda)
            if commit:
                target_history.add_pending_items()
        if commit:
            with transaction(sa_session):
                sa_session.commit()
        return hda

    def copy(self, parent_id=None, target_folder=None, flush=True):
        sa_session = object_session(self)
        ldda = LibraryDatasetDatasetAssociation(
            name=self.name,
            info=self.info,
            blurb=self.blurb,
            peek=self.peek,
            tool_version=self.tool_version,
            extension=self.extension,
            dbkey=self.dbkey,
            dataset=self.dataset,
            visible=self.visible,
            deleted=self.deleted,
            parent_id=parent_id,
            copied_from_library_dataset_dataset_association=self,
            folder=target_folder,
        )

        tag_manager = galaxy.model.tags.GalaxyTagHandler(sa_session)
        src_ldda_tags = tag_manager.get_tags_str(self.tags)
        tag_manager.apply_item_tags(user=self.user, item=ldda, tags_str=src_ldda_tags)

        sa_session.add(ldda)
        with transaction(sa_session):
            sa_session.commit()
        # Need to set after flushed, as MetadataFiles require dataset.id
        ldda.metadata = self.metadata
        with transaction(sa_session):
            sa_session.commit()
        return ldda

    def clear_associated_files(self, metadata_safe=False, purge=False):
        return

    def get_access_roles(self, security_agent):
        return self.dataset.get_access_roles(security_agent)

    def get_manage_permissions_roles(self, security_agent):
        return self.dataset.get_manage_permissions_roles(security_agent)

    def has_manage_permissions_roles(self, security_agent):
        return self.dataset.has_manage_permissions_roles(security_agent)

    def _serialize(self, id_encoder, serialization_options):
        rval = super()._serialize(id_encoder, serialization_options)
        self._handle_serialize_files(id_encoder, serialization_options, rval)
        return rval

    def to_dict(self, view="collection"):
        # Since this class is a proxy to rather complex attributes we want to
        # display in other objects, we can't use the simpler method used by
        # other model classes.
        ldda = self
        try:
            file_size = int(ldda.get_size())
        except OSError:
            file_size = 0

        # TODO: render tags here
        rval = dict(
            id=ldda.id,
            hda_ldda="ldda",
            model_class=self.__class__.__name__,
            name=ldda.name,
            deleted=ldda.deleted,
            visible=ldda.visible,
            state=ldda.state,
            library_dataset_id=ldda.library_dataset_id,
            file_size=file_size,
            file_name=ldda.get_file_name(),
            update_time=ldda.update_time.isoformat(),
            file_ext=ldda.ext,
            data_type=f"{ldda.datatype.__class__.__module__}.{ldda.datatype.__class__.__name__}",
            genome_build=ldda.dbkey,
            misc_info=ldda.info,
            misc_blurb=ldda.blurb,
            created_from_basename=ldda.created_from_basename,
        )
        if ldda.dataset.uuid is None:
            rval["uuid"] = None
        else:
            rval["uuid"] = str(ldda.dataset.uuid)
        rval["parent_library_id"] = ldda.library_dataset.folder.parent_library.id
        if ldda.extended_metadata is not None:
            rval["extended_metadata"] = ldda.extended_metadata.data
        for name in ldda.metadata.spec.keys():
            val = ldda.metadata.get(name)
            if isinstance(val, MetadataFile):
                val = val.get_file_name()
            # If no value for metadata, look in datatype for metadata.
            elif val is None and hasattr(ldda.datatype, name):
                val = getattr(ldda.datatype, name)
            rval[f"metadata_{name}"] = val
        return rval

    def update_parent_folder_update_times(self):
        # sets the update_time for all continaing folders up the tree
        ldda = self

        sql = text(
            """
                WITH RECURSIVE parent_folders_of(folder_id) AS
                    (SELECT folder_id
                    FROM library_dataset
                    WHERE id = :library_dataset_id
                    UNION ALL
                    SELECT library_folder.parent_id
                    FROM library_folder, parent_folders_of
                    WHERE library_folder.id = parent_folders_of.folder_id )
                UPDATE library_folder
                SET update_time =
                    (SELECT update_time
                    FROM library_dataset_dataset_association
                    WHERE id = :ldda_id)
                WHERE exists (SELECT 1 FROM parent_folders_of
                    WHERE library_folder.id = parent_folders_of.folder_id)
            """
        )

        with object_session(self).bind.connect() as conn, conn.begin():
            ret = conn.execute(sql, {"library_dataset_id": ldda.library_dataset_id, "ldda_id": ldda.id})

        if ret.rowcount < 1:
            log.warning(f"Attempt to updated parent folder times failed: {ret.rowcount} records updated.")


class ExtendedMetadata(Base, RepresentById):
    __tablename__ = "extended_metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    children: Mapped[List["ExtendedMetadataIndex"]] = relationship(back_populates="extended_metadata")

    def __init__(self, data):
        self.data = data


class ExtendedMetadataIndex(Base, RepresentById):
    __tablename__ = "extended_metadata_index"

    id: Mapped[int] = mapped_column(primary_key=True)
    extended_metadata_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("extended_metadata.id", onupdate="CASCADE", ondelete="CASCADE"), index=True
    )
    path: Mapped[Optional[str]] = mapped_column(String(255))
    value: Mapped[Optional[str]] = mapped_column(TEXT)
    extended_metadata: Mapped[Optional["ExtendedMetadata"]] = relationship(back_populates="children")

    def __init__(self, extended_metadata, path, value):
        self.extended_metadata = extended_metadata
        self.path = path
        self.value = value


class LibraryInfoAssociation(Base, RepresentById):
    __tablename__ = "library_info_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    library_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library.id"), index=True)
    form_definition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("form_definition.id"), index=True)
    form_values_id: Mapped[Optional[int]] = mapped_column(ForeignKey("form_values.id"), index=True)
    inheritable: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)

    library: Mapped[Optional["Library"]] = relationship(
        primaryjoin=(
            lambda: and_(
                LibraryInfoAssociation.library_id == Library.id,
                not_(LibraryInfoAssociation.deleted),  # type:ignore[arg-type]
            )
        ),
    )
    template: Mapped[Optional["FormDefinition"]] = relationship(
        primaryjoin=lambda: LibraryInfoAssociation.form_definition_id == FormDefinition.id
    )
    info: Mapped[Optional["FormValues"]] = relationship(
        primaryjoin=lambda: LibraryInfoAssociation.form_values_id == FormValues.id
    )

    def __init__(self, library, form_definition, info, inheritable=False):
        self.library = library
        self.template = form_definition
        self.info = info
        self.inheritable = inheritable


class LibraryFolderInfoAssociation(Base, RepresentById):
    __tablename__ = "library_folder_info_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    library_folder_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library_folder.id"), index=True)
    form_definition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("form_definition.id"), index=True)
    form_values_id: Mapped[Optional[int]] = mapped_column(ForeignKey("form_values.id"), index=True)
    inheritable: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)

    folder: Mapped[Optional["LibraryFolder"]] = relationship(
        primaryjoin=(
            lambda: (LibraryFolderInfoAssociation.library_folder_id == LibraryFolder.id)
            & (not_(LibraryFolderInfoAssociation.deleted))
        ),
    )
    template: Mapped[Optional["FormDefinition"]] = relationship(
        primaryjoin=(lambda: LibraryFolderInfoAssociation.form_definition_id == FormDefinition.id)
    )
    info: Mapped[Optional["FormValues"]] = relationship(
        primaryjoin=(lambda: LibraryFolderInfoAssociation.form_values_id == FormValues.id)
    )

    def __init__(self, folder, form_definition, info, inheritable=False):
        self.folder = folder
        self.template = form_definition
        self.info = info
        self.inheritable = inheritable


class LibraryDatasetDatasetInfoAssociation(Base, RepresentById):
    __tablename__ = "library_dataset_dataset_info_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    library_dataset_dataset_association_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("library_dataset_dataset_association.id"), index=True
    )
    form_definition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("form_definition.id"), index=True)
    form_values_id: Mapped[Optional[int]] = mapped_column(ForeignKey("form_values.id"), index=True)
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)

    library_dataset_dataset_association: Mapped[Optional["LibraryDatasetDatasetAssociation"]] = relationship(
        primaryjoin=(
            lambda: (
                LibraryDatasetDatasetInfoAssociation.library_dataset_dataset_association_id
                == LibraryDatasetDatasetAssociation.id
            )
            & (not_(LibraryDatasetDatasetInfoAssociation.deleted))
        ),
    )
    template: Mapped[Optional["FormDefinition"]] = relationship(
        primaryjoin=(lambda: LibraryDatasetDatasetInfoAssociation.form_definition_id == FormDefinition.id),
    )
    info: Mapped[Optional["FormValues"]] = relationship(
        primaryjoin=(lambda: LibraryDatasetDatasetInfoAssociation.form_values_id == FormValues.id)
    )

    def __init__(self, library_dataset_dataset_association, form_definition, info):
        # TODO: need to figure out if this should be inheritable to the associated LibraryDataset
        self.library_dataset_dataset_association = library_dataset_dataset_association
        self.template = form_definition
        self.info = info

    @property
    def inheritable(self):
        return True  # always allow inheriting, used for replacement


class ImplicitlyConvertedDatasetAssociation(Base, Serializable):
    __tablename__ = "implicitly_converted_dataset_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    hda_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history_dataset_association.id"), index=True)
    ldda_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library_dataset_dataset_association.id"), index=True)
    hda_parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history_dataset_association.id"), index=True)
    ldda_parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("library_dataset_dataset_association.id"), index=True
    )
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    metadata_safe: Mapped[Optional[bool]] = mapped_column(index=True, default=True)
    type: Mapped[Optional[str]] = mapped_column(TrimmedString(255))

    parent_hda: Mapped[Optional["HistoryDatasetAssociation"]] = relationship(
        primaryjoin=(lambda: ImplicitlyConvertedDatasetAssociation.hda_parent_id == HistoryDatasetAssociation.id),
        back_populates="implicitly_converted_datasets",
    )
    dataset_ldda: Mapped[Optional["LibraryDatasetDatasetAssociation"]] = relationship(
        primaryjoin=(lambda: ImplicitlyConvertedDatasetAssociation.ldda_id == LibraryDatasetDatasetAssociation.id),
        back_populates="implicitly_converted_parent_datasets",
    )
    dataset: Mapped[Optional["HistoryDatasetAssociation"]] = relationship(
        primaryjoin=(lambda: ImplicitlyConvertedDatasetAssociation.hda_id == HistoryDatasetAssociation.id),
        back_populates="implicitly_converted_parent_datasets",
    )
    parent_ldda: Mapped[Optional["LibraryDatasetDatasetAssociation"]] = relationship(
        primaryjoin=(
            lambda: ImplicitlyConvertedDatasetAssociation.ldda_parent_id == LibraryDatasetDatasetAssociation.table.c.id
        ),
        back_populates="implicitly_converted_datasets",
    )

    def __init__(
        self,
        id=None,
        parent=None,
        dataset=None,
        file_type=None,
        deleted=False,
        purged=False,
        metadata_safe=True,
        for_import=False,
    ):
        self.id = id
        add_object_to_object_session(self, dataset)
        if isinstance(dataset, HistoryDatasetAssociation):
            self.dataset = dataset
        elif isinstance(dataset, LibraryDatasetDatasetAssociation):
            self.dataset_ldda = dataset
        elif not for_import:
            raise AttributeError(f"Unknown dataset type provided for dataset: {type(dataset)}")
            # else if for import - these connections might not have been included in the store,
            # recover the data we can?
        if isinstance(parent, HistoryDatasetAssociation):
            self.parent_hda = parent
        elif isinstance(parent, LibraryDatasetDatasetAssociation):
            self.parent_ldda = parent
        elif not for_import:
            raise AttributeError(f"Unknown dataset type provided for parent: {type(parent)}")
            # else if for import - these connections might not have been included in the store,
            # recover the data we can?
        self.type = file_type
        self.deleted = deleted
        self.purged = purged
        self.metadata_safe = metadata_safe

    def clear(self, purge=False, delete_dataset=True):
        self.deleted = True
        if self.dataset:
            if delete_dataset:
                self.dataset.deleted = True
            if purge:
                self.dataset.purged = True
        if purge and self.dataset.deleted:  # do something with purging
            self.purged = True
            try:
                os.unlink(self.get_file_name())
            except Exception as e:
                log.error(f"Failed to purge associated file ({self.get_file_name()}) from disk: {unicodify(e)}")

    def _serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            file_type=self.type,
        )
        if self.parent_hda:
            rval["parent_hda"] = serialization_options.get_identifier(id_encoder, self.parent_hda)
        if self.dataset:
            rval["hda"] = serialization_options.get_identifier(id_encoder, self.dataset)
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval


DEFAULT_COLLECTION_NAME = "Unnamed Collection"


class InnerCollectionFilter(NamedTuple):
    column: str
    operator_function: Callable
    expected_value: Union[str, int, float, bool]

    def produce_filter(self, table):
        return self.operator_function(getattr(table, self.column), self.expected_value)


class DatasetCollection(Base, Dictifiable, UsesAnnotations, Serializable):
    __tablename__ = "dataset_collection"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_type: Mapped[str] = mapped_column(Unicode(255))
    populated_state: Mapped[str] = mapped_column(TrimmedString(64), default="ok")
    populated_state_message: Mapped[Optional[str]] = mapped_column(TEXT)
    element_count: Mapped[Optional[int]]
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)

    elements: Mapped[List["DatasetCollectionElement"]] = relationship(
        primaryjoin=(lambda: DatasetCollection.id == DatasetCollectionElement.dataset_collection_id),
        back_populates="collection",
        order_by=lambda: DatasetCollectionElement.element_index,
    )

    dict_collection_visible_keys = ["id", "collection_type"]
    dict_element_visible_keys = ["id", "collection_type"]

    populated_states = DatasetCollectionPopulatedState

    def __init__(self, id=None, collection_type=None, populated=True, element_count=None):
        self.id = id
        self.collection_type = collection_type
        if not populated:
            self.populated_state = DatasetCollection.populated_states.NEW
        self.element_count = element_count

    def _build_nested_collection_attributes_stmt(
        self,
        collection_attributes: Optional[Iterable[str]] = None,
        element_attributes: Optional[Iterable[str]] = None,
        hda_attributes: Optional[Iterable[str]] = None,
        dataset_attributes: Optional[Iterable[str]] = None,
        dataset_permission_attributes: Optional[Iterable[str]] = None,
        return_entities: Optional[
            Iterable[
                Union[
                    Type[HistoryDatasetAssociation],
                    Type[Dataset],
                    Type[DatasetPermissions],
                    Type["DatasetCollection"],
                    Type["DatasetCollectionElement"],
                ]
            ]
        ] = None,
        inner_filter: Optional[InnerCollectionFilter] = None,
    ):
        collection_attributes = collection_attributes or ()
        element_attributes = element_attributes or ()
        hda_attributes = hda_attributes or ()
        dataset_attributes = dataset_attributes or ()
        dataset_permission_attributes = dataset_permission_attributes or ()
        return_entities = return_entities or ()
        dataset_collection = self
        dc = alias(DatasetCollection.__table__)
        dce = alias(DatasetCollectionElement.__table__)
        depth_collection_type = dataset_collection.collection_type
        order_by_columns = [dce.c.element_index]
        nesting_level = 0

        def attribute_columns(column_collection, attributes, nesting_level=None):
            label_fragment = f"_{nesting_level}" if nesting_level is not None else ""
            return [getattr(column_collection, a).label(f"{a}{label_fragment}") for a in attributes]

        q = (
            select(
                *attribute_columns(dce.c, element_attributes, nesting_level),
                *attribute_columns(dc.c, collection_attributes, nesting_level),
            )
            .select_from(dce, dc)
            .join(dce, dce.c.dataset_collection_id == dc.c.id)
            .filter(dc.c.id == dataset_collection.id)
        )

        while ":" in depth_collection_type:
            nesting_level += 1
            inner_dce = alias(DatasetCollectionElement.__table__)
            inner_dc = alias(DatasetCollection.__table__)
            order_by_columns.append(inner_dce.c.element_index)
            q = q.outerjoin(inner_dce, inner_dce.c.dataset_collection_id == dce.c.child_collection_id)
            if collection_attributes:
                q = q.join(inner_dc, inner_dc.c.id == dce.c.child_collection_id)
                q = q.add_columns(
                    *attribute_columns(inner_dc.c, collection_attributes, nesting_level),
                )
            q = q.add_columns(*attribute_columns(inner_dce.c, element_attributes, nesting_level))
            dce = inner_dce
            dc = inner_dc
            depth_collection_type = depth_collection_type.split(":", 1)[1]
        if inner_filter:
            q = q.filter(inner_filter.produce_filter(dc.c))

        if (
            hda_attributes
            or dataset_attributes
            or dataset_permission_attributes
            or return_entities
            and not return_entities == (DatasetCollectionElement,)
        ):
            q = q.join(HistoryDatasetAssociation).join(Dataset)
        if dataset_permission_attributes:
            q = q.join(DatasetPermissions)
        q = (
            q.add_columns(*attribute_columns(HistoryDatasetAssociation, hda_attributes))
            .add_columns(*attribute_columns(Dataset, dataset_attributes))
            .add_columns(*attribute_columns(DatasetPermissions, dataset_permission_attributes))
        )
        for entity in return_entities:
            q = q.add_columns(entity)
            if entity == DatasetCollectionElement:
                q = q.filter(entity.id == dce.c.id)

        q = q.order_by(*order_by_columns)
        return q

    @property
    def elements_deleted(self):
        if not hasattr(self, "_elements_deleted"):
            if session := object_session(self):
                stmt = self._build_nested_collection_attributes_stmt(
                    hda_attributes=("deleted",), dataset_attributes=("deleted",)
                )
                stmt = stmt.exists().where(or_(HistoryDatasetAssociation.deleted == true(), Dataset.deleted == true()))
                self._elements_deleted = session.execute(select(stmt)).scalar()
            else:
                self._elements_deleted = False
                for dataset_instance in self.dataset_instances:
                    if dataset_instance.deleted or dataset_instance.dataset.deleted:
                        self._elements_deleted = True
                        break
        return self._elements_deleted

    @property
    def dataset_states_and_extensions_summary(self):
        if not hasattr(self, "_dataset_states_and_extensions_summary"):
            stmt = self._build_nested_collection_attributes_stmt(
                hda_attributes=("extension",), dataset_attributes=("state",)
            )
            # With DISTINCT, all columns that appear in the ORDER BY clause must appear in the SELECT clause.
            stmt = stmt.add_columns(*stmt._order_by_clauses)
            stmt = stmt.distinct()

            tuples = object_session(self).execute(stmt)

            extensions = set()
            states = set()
            for extension, state, *_ in tuples:  # we discard the added columns from the order-by clause
                states.add(state)
                extensions.add(extension)

            self._dataset_states_and_extensions_summary = (states, extensions)

        return self._dataset_states_and_extensions_summary

    @property
    def has_deferred_data(self):
        if not hasattr(self, "_has_deferred_data"):
            has_deferred_data = False
            if object_session(self):
                # TODO: Optimize by just querying without returning the states...
                stmt = self._build_nested_collection_attributes_stmt(dataset_attributes=("state",))
                tuples = object_session(self).execute(stmt)
                for (state,) in tuples:
                    if state == Dataset.states.DEFERRED:
                        has_deferred_data = True
                        break
            else:
                # This will be in a remote tool evaluation context, so can't query database
                for dataset_element in self.dataset_elements_and_identifiers():
                    if dataset_element.hda.state == Dataset.states.DEFERRED:
                        has_deferred_data = True
                        break
            self._has_deferred_data = has_deferred_data

        return self._has_deferred_data

    @property
    def populated_optimized(self):
        if not hasattr(self, "_populated_optimized"):
            if not self.id:
                return self.populated
            _populated_optimized = True
            if ":" not in self.collection_type:
                _populated_optimized = self.populated_state == DatasetCollection.populated_states.OK
            else:
                stmt = self._build_nested_collection_attributes_stmt(
                    collection_attributes=("populated_state",),
                    inner_filter=InnerCollectionFilter(
                        "populated_state", operator.__ne__, DatasetCollection.populated_states.OK
                    ),
                )
                stmt = stmt.subquery()
                stmt = select(~exists(stmt))
                session = object_session(self)
                _populated_optimized = session.scalar(stmt)

            self._populated_optimized = _populated_optimized

        return self._populated_optimized

    @property
    def populated(self):
        top_level_populated = self.populated_state == DatasetCollection.populated_states.OK
        if top_level_populated and self.has_subcollections:
            return all(e.child_collection and e.child_collection.populated for e in self.elements)
        return top_level_populated

    @property
    def dataset_action_tuples(self):
        if not hasattr(self, "_dataset_action_tuples"):
            stmt = self._build_nested_collection_attributes_stmt(dataset_permission_attributes=("action", "role_id"))
            tuples = object_session(self).execute(stmt)
            self._dataset_action_tuples = [(action, role_id) for action, role_id in tuples if action is not None]
        return self._dataset_action_tuples

    @property
    def element_identifiers_extensions_paths_and_metadata_files(
        self,
    ) -> List[List[Any]]:
        results = []
        if object_session(self):
            stmt = self._build_nested_collection_attributes_stmt(
                element_attributes=("element_identifier",),
                hda_attributes=("extension",),
                return_entities=(HistoryDatasetAssociation, Dataset),
            )
            tuples = object_session(self).execute(stmt)  # type:ignore[union-attr]
            # element_identifiers, extension, path
            for row in tuples:
                result = [row[:-3], row.extension, row.Dataset.get_file_name()]
                hda = row.HistoryDatasetAssociation
                result.append(hda.get_metadata_file_paths_and_extensions())
                results.append(result)
        else:
            # This will be in a remote tool evaluation context, so can't query database
            for dataset_element in self.dataset_elements_and_identifiers():
                # Let's pretend name is element identifier
                results.append(
                    [
                        dataset_element._identifiers,
                        dataset_element.hda.extension,
                        dataset_element.hda.get_file_name(),
                        dataset_element.hda.get_metadata_file_paths_and_extensions(),
                    ]
                )
        return results

    @property
    def waiting_for_elements(self):
        top_level_waiting = self.populated_state == DatasetCollection.populated_states.NEW
        if not top_level_waiting and self.has_subcollections:
            return any(e.child_collection.waiting_for_elements for e in self.elements)
        return top_level_waiting

    def mark_as_populated(self):
        self.populated_state = DatasetCollection.populated_states.OK

    def handle_population_failed(self, message):
        self.populated_state = DatasetCollection.populated_states.FAILED
        self.populated_state_message = message

    def finalize(self, collection_type_description):
        # All jobs have written out their elements - everything should be populated
        # but might not be - check that second case! (TODO)
        self.mark_as_populated()
        if self.has_subcollections and collection_type_description.has_subcollections():
            for element in self.elements:
                element.child_collection.finalize(collection_type_description.child_collection_type_description())

    @property
    def dataset_instances(self):
        db_session = object_session(self)
        if db_session and self.id:
            stmt = self._build_nested_collection_attributes_stmt(return_entities=(HistoryDatasetAssociation,))
            tuples = db_session.execute(stmt).all()
            return [tuple[0] for tuple in tuples]
        else:
            # Sessionless context
            instances = []
            for element in self.elements:
                if element.is_collection:
                    instances.extend(element.child_collection.dataset_instances)
                else:
                    instance = element.dataset_instance
                    instances.append(instance)
            return instances

    @property
    def dataset_elements(self):
        db_session = object_session(self)
        if db_session and self.id:
            stmt = self._build_nested_collection_attributes_stmt(return_entities=(DatasetCollectionElement,))
            tuples = db_session.execute(stmt).all()
            return [tuple[0] for tuple in tuples]
        elements = []
        for element in self.elements:
            if element.is_collection:
                elements.extend(element.child_collection.dataset_elements)
            else:
                elements.append(element)
        return elements

    def dataset_elements_and_identifiers(self, identifiers=None):
        # Used only in remote tool evaluation context
        elements = []
        if identifiers is None:
            identifiers = []
        for element in self.elements:
            _identifiers = identifiers[:]
            _identifiers.append(element.element_identifier)
            if element.is_collection:
                elements.extend(element.child_collection.dataset_elements_and_identifiers(_identifiers))
            else:
                element._identifiers = _identifiers
                elements.append(element)
        return elements

    @property
    def first_dataset_element(self) -> Optional["DatasetCollectionElement"]:
        for element in self.elements:
            if element.is_collection:
                first_element = element.child_collection.first_dataset_element
                if first_element:
                    return first_element
            else:
                return element
        return None

    @property
    def state(self):
        # TODO: DatasetCollection state handling...
        return "ok"

    def validate(self):
        if self.collection_type is None:
            raise Exception("Each dataset collection must define a collection type.")

    def __getitem__(self, key):
        if isinstance(key, int):
            try:
                return self.elements[key]
            except IndexError:
                pass
        else:
            # This might be a peformance issue for large collection, but we don't use this a lot
            for element in self.elements:
                if element.element_identifier == key:
                    return element
        get_by_attribute = "element_index" if isinstance(key, int) else "element_identifier"
        error_message = f"Dataset collection has no {get_by_attribute} with key {key}."
        raise KeyError(error_message)

    def copy(
        self,
        destination=None,
        element_destination=None,
        dataset_instance_attributes=None,
        flush=True,
        minimize_copies=False,
    ):
        new_collection = DatasetCollection(collection_type=self.collection_type, element_count=self.element_count)
        for element in self.elements:
            element.copy_to_collection(
                new_collection,
                destination=destination,
                element_destination=element_destination,
                dataset_instance_attributes=dataset_instance_attributes,
                flush=flush,
                minimize_copies=minimize_copies,
            )
        object_session(self).add(new_collection)
        if flush:
            session = object_session(self)
            with transaction(session):
                session.commit()
        return new_collection

    def replace_failed_elements(self, replacements):
        stmt = self._build_nested_collection_attributes_stmt(
            return_entities=[DatasetCollectionElement], hda_attributes=["id"]
        )
        tuples = object_session(self).execute(stmt).all()
        hda_id_to_element = dict(tuples)
        for failed, replacement in replacements.items():
            element = hda_id_to_element.get(failed.id)
            if element:
                element.hda = replacement

    def set_from_dict(self, new_data):
        # Nothing currently editable in this class.
        return {}

    @property
    def has_subcollections(self):
        return ":" in self.collection_type

    def _serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            type=self.collection_type,
            populated_state=self.populated_state,
            populated_state_message=self.populated_state_message,
            elements=[e.serialize(id_encoder, serialization_options) for e in self.elements],
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval


class DatasetCollectionInstance(HasName, UsesCreateAndUpdateTime):
    @property
    def state(self):
        return self.collection.state

    @property
    def populated(self):
        return self.collection.populated

    @property
    def dataset_instances(self):
        return self.collection.dataset_instances

    def display_name(self):
        return self.get_display_name()

    def _base_to_dict(self, view):
        return dict(
            id=self.id,
            name=self.name,
            collection_id=self.collection_id,
            collection_type=self.collection.collection_type,
            populated=self.populated,
            populated_state=self.collection.populated_state,
            populated_state_message=self.collection.populated_state_message,
            element_count=self.collection.element_count,
            elements_datatypes=list(self.dataset_dbkeys_and_extensions_summary[1]),
            type="collection",  # contents type (distinguished from file or folder (in case of library))
        )

    def set_from_dict(self, new_data):
        """
        Set object attributes to the values in dictionary new_data limiting
        to only those keys in dict_element_visible_keys.

        Returns a dictionary of the keys, values that have been changed.
        """
        # precondition: keys are proper, values are parsed and validated
        changed = self.collection.set_from_dict(new_data)

        # unknown keys are ignored here
        for key in (k for k in new_data.keys() if k in self.editable_keys):
            new_val = new_data[key]
            old_val = self.__getattribute__(key)
            if new_val == old_val:
                continue

            self.__setattr__(key, new_val)
            changed[key] = new_val

        return changed

    @property
    def has_deferred_data(self):
        return self.collection.has_deferred_data


class HistoryDatasetCollectionAssociation(
    Base,
    DatasetCollectionInstance,
    HasTags,
    Dictifiable,
    UsesAnnotations,
    Serializable,
):
    """Associates a DatasetCollection with a History."""

    __tablename__ = "history_dataset_collection_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dataset_collection.id"), index=True)
    history_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history.id"), index=True)
    name: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    hid: Mapped[Optional[int]]
    visible: Mapped[Optional[bool]]
    deleted: Mapped[Optional[bool]] = mapped_column(default=False)
    copied_from_history_dataset_collection_association_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("history_dataset_collection_association.id")
    )
    implicit_output_name: Mapped[Optional[str]] = mapped_column(Unicode(255))
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    implicit_collection_jobs_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("implicit_collection_jobs.id"), index=True
    )
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, index=True, nullable=True)

    collection = relationship("DatasetCollection")
    history: Mapped[Optional["History"]] = relationship(back_populates="dataset_collections")

    copied_from_history_dataset_collection_association = relationship(
        "HistoryDatasetCollectionAssociation",
        primaryjoin=copied_from_history_dataset_collection_association_id == id,
        remote_side=[id],
        uselist=False,
    )
    implicit_input_collections: Mapped[List["ImplicitlyCreatedDatasetCollectionInput"]] = relationship(
        primaryjoin=(
            lambda: HistoryDatasetCollectionAssociation.id
            == ImplicitlyCreatedDatasetCollectionInput.dataset_collection_id
        ),
    )
    implicit_collection_jobs = relationship("ImplicitCollectionJobs", uselist=False)
    job: Mapped[Optional["Job"]] = relationship(
        back_populates="history_dataset_collection_associations",
        uselist=False,
    )
    tags: Mapped[List["HistoryDatasetCollectionTagAssociation"]] = relationship(
        order_by=lambda: HistoryDatasetCollectionTagAssociation.id,
        back_populates="dataset_collection",
    )
    annotations: Mapped[List["HistoryDatasetCollectionAssociationAnnotationAssociation"]] = relationship(
        order_by=lambda: HistoryDatasetCollectionAssociationAnnotationAssociation.id,
        back_populates="history_dataset_collection",
    )
    ratings: Mapped[List["HistoryDatasetCollectionRatingAssociation"]] = relationship(
        order_by=lambda: HistoryDatasetCollectionRatingAssociation.id,
        back_populates="dataset_collection",
    )
    creating_job_associations: Mapped[List["JobToOutputDatasetCollectionAssociation"]] = relationship(viewonly=True)

    dict_dbkeysandextensions_visible_keys = ["dbkeys", "extensions"]
    editable_keys = ("name", "deleted", "visible")
    _job_state_summary = None

    def __init__(self, deleted=False, visible=True, **kwd):
        super().__init__(**kwd)
        # Since deleted property is shared between history and dataset collections,
        # it could be on either table - some places in the code however it is convient
        # it is on instance instead of collection.
        self.deleted = deleted
        self.visible = visible
        self.implicit_input_collections = self.implicit_input_collections or []

    @property
    def history_content_type(self):
        return "dataset_collection"

    # TODO: down into DatasetCollectionInstance
    content_type = "dataset_collection"

    @hybrid.hybrid_property
    def type_id(self):
        return "-".join((self.content_type, str(self.id)))

    @type_id.expression  # type: ignore[no-redef]
    def type_id(cls):
        return (type_coerce(cls.content_type, Unicode) + "-" + type_coerce(cls.id, Unicode)).label("type_id")

    @property
    def job_source_type(self):
        if self.implicit_collection_jobs_id:
            return "ImplicitCollectionJobs"
        elif self.job_id:
            return "Job"
        else:
            return None

    @property
    def job_state_summary(self):
        """
        Aggregate counts of jobs by state, stored in a JobStateSummary object.
        """
        if not self._job_state_summary:
            self._job_state_summary = self._get_job_state_summary()
            # if summary exists, but there are no jobs, load zeroes for all other counts (otherwise they will be None)
            if self._job_state_summary and self._job_state_summary.all_jobs == 0:
                zeroes = [0] * (len(Job.states) + 1)
                self._job_state_summary = JobStateSummary._make(zeroes)

        return self._job_state_summary

    def _get_job_state_summary(self):
        def build_statement():
            state_label = "state"  # used to generate `SELECT job.state AS state`, and then refer to it in aggregates.

            # Select job states joining on icjja > icj > hdca
            # (We are selecting Job.id in addition to Job.state because otherwise the UNION operation
            #  will get rid of duplicates, making aggregates meaningless.)
            subq1 = (
                select(Job.id, Job.state.label(state_label))
                .join(ImplicitCollectionJobsJobAssociation, ImplicitCollectionJobsJobAssociation.job_id == Job.id)
                .join(
                    ImplicitCollectionJobs,
                    ImplicitCollectionJobs.id == ImplicitCollectionJobsJobAssociation.implicit_collection_jobs_id,
                )
                .join(
                    HistoryDatasetCollectionAssociation,
                    HistoryDatasetCollectionAssociation.implicit_collection_jobs_id == ImplicitCollectionJobs.id,
                )
                .where(HistoryDatasetCollectionAssociation.id == self.id)
            )

            # Select job states joining on hdca
            subq2 = (
                select(Job.id, Job.state.label(state_label))
                .join(HistoryDatasetCollectionAssociation, HistoryDatasetCollectionAssociation.job_id == Job.id)
                .where(HistoryDatasetCollectionAssociation.id == self.id)
            )

            # Combine subqueries
            subq = subq1.union(subq2)

            # Build and return final query
            stm = select().select_from(subq)
            # Add aggregate columns for each job state
            for state in enum_values(Job.states):
                col = func.sum(case((column(state_label) == state, 1), else_=0)).label(state)
                stm = stm.add_columns(col)
            # Add aggregate column for all jobs
            col = func.count().label("all_jobs")
            stm = stm.add_columns(col)
            return stm

        if not object_session(self):
            return None  # no session means object is not persistant; therefore, it has no associated jobs.

        engine = object_session(self).bind
        with engine.connect() as conn:
            counts = conn.execute(build_statement()).one()
            assert len(counts) == len(Job.states) + 1  # Verify all job states + all jobs are counted
            return JobStateSummary._make(counts)

    @property
    def job_state_summary_dict(self):
        if self.job_state_summary:
            return self.job_state_summary._asdict()

    @property
    def dataset_dbkeys_and_extensions_summary(self):
        if not hasattr(self, "_dataset_dbkeys_and_extensions_summary"):
            stmt = self.collection._build_nested_collection_attributes_stmt(hda_attributes=("_metadata", "extension"))
            tuples = object_session(self).execute(stmt)

            extensions = set()
            dbkeys = set()
            for row in tuples:
                if row is not None:
                    dbkey_field = row._metadata.get("dbkey")
                    if isinstance(dbkey_field, list):
                        for dbkey in dbkey_field:
                            dbkeys.add(dbkey)
                    else:
                        dbkeys.add(dbkey_field)
                    if row.extension:
                        extensions.add(row.extension)
            self._dataset_dbkeys_and_extensions_summary = (dbkeys, extensions)
        return self._dataset_dbkeys_and_extensions_summary

    @property
    def job_source_id(self):
        return self.implicit_collection_jobs_id or self.job_id

    def touch(self):
        # cause an update to be emitted, so that e.g. update_time is incremented and triggers are notified
        if getattr(self, "name", None):
            # attribute to flag doesn't really matter as long as it's not null (and primary key also doesn't work)
            flag_modified(self, "name")
            if self.collection:
                flag_modified(self.collection, "collection_type")

    @overload
    def to_hda_representative(self, multiple: Literal[False] = False) -> Optional[HistoryDatasetAssociation]: ...

    @overload
    def to_hda_representative(self, multiple: Literal[True]) -> List[HistoryDatasetAssociation]: ...

    def to_hda_representative(
        self, multiple: bool = False
    ) -> Union[List[HistoryDatasetAssociation], Optional[HistoryDatasetAssociation]]:
        rval = []
        for dataset in self.collection.dataset_elements:
            rval.append(dataset.dataset_instance)
            if multiple is False:
                break
        if multiple:
            return rval
        return rval[0] if rval else None

    def _serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            display_name=self.display_name(),
            state=self.state,
            hid=self.hid,
            collection=self.collection.serialize(id_encoder, serialization_options),
            implicit_output_name=self.implicit_output_name,
        )
        if self.history:
            rval["history_encoded_id"] = serialization_options.get_identifier(id_encoder, self.history)

        implicit_input_collections = []
        for implicit_input_collection in self.implicit_input_collections:
            input_hdca = implicit_input_collection.input_dataset_collection
            implicit_input_collections.append(
                {
                    "name": implicit_input_collection.name,
                    "input_dataset_collection": serialization_options.get_identifier(id_encoder, input_hdca),
                }
            )
        if implicit_input_collections:
            rval["implicit_input_collections"] = implicit_input_collections

        # Handle copied_from_history_dataset_association information...
        copied_from_history_dataset_collection_association_chain = []
        src_hdca = self
        while src_hdca.copied_from_history_dataset_collection_association:
            src_hdca = src_hdca.copied_from_history_dataset_collection_association
            copied_from_history_dataset_collection_association_chain.append(
                serialization_options.get_identifier(id_encoder, src_hdca)
            )
        rval["copied_from_history_dataset_collection_association_id_chain"] = (
            copied_from_history_dataset_collection_association_chain
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def to_dict(self, view="collection"):
        original_dict_value = super().to_dict(view=view)
        if view == "dbkeysandextensions":
            (dbkeys, extensions) = self.dataset_dbkeys_and_extensions_summary
            dict_value = dict(
                dbkey=dbkeys.pop() if len(dbkeys) == 1 else "?",
                extension=extensions.pop() if len(extensions) == 1 else "auto",
            )
        else:
            dict_value = dict(
                hid=self.hid,
                history_id=self.history.id,
                history_content_type=self.history_content_type,
                visible=self.visible,
                deleted=self.deleted,
                job_source_id=self.job_source_id,
                job_source_type=self.job_source_type,
                job_state_summary=self.job_state_summary_dict,
                create_time=self.create_time.isoformat(),
                update_time=self.update_time.isoformat(),
                **self._base_to_dict(view=view),
            )

        dict_value.update(original_dict_value)

        return dict_value

    def add_implicit_input_collection(self, name, history_dataset_collection):
        self.implicit_input_collections.append(
            ImplicitlyCreatedDatasetCollectionInput(name, history_dataset_collection)
        )

    def find_implicit_input_collection(self, name):
        matching_collection = None
        for implicit_input_collection in self.implicit_input_collections:
            if implicit_input_collection.name == name:
                matching_collection = implicit_input_collection.input_dataset_collection
                break
        return matching_collection

    def copy(
        self,
        element_destination=None,
        dataset_instance_attributes=None,
        flush=True,
        set_hid=True,
        minimize_copies=False,
    ):
        """
        Create a copy of this history dataset collection association. Copy
        underlying collection.
        """
        hdca = HistoryDatasetCollectionAssociation(
            hid=self.hid,
            collection=None,
            visible=self.visible,
            deleted=self.deleted,
            name=self.name,
            copied_from_history_dataset_collection_association=self,
        )
        if self.implicit_collection_jobs_id:
            hdca.implicit_collection_jobs_id = self.implicit_collection_jobs_id
        elif self.job_id:
            hdca.job_id = self.job_id

        collection_copy = self.collection.copy(
            destination=hdca,
            element_destination=element_destination,
            dataset_instance_attributes=dataset_instance_attributes,
            flush=False,
            minimize_copies=minimize_copies,
        )
        hdca.collection = collection_copy
        object_session(self).add(hdca)
        hdca.copy_tags_from(self.history.user, self)
        if element_destination and set_hid:
            element_destination.stage_addition(hdca)
            element_destination.add_pending_items()
        if flush:
            session = object_session(self)
            with transaction(session):
                session.commit()
        return hdca

    @property
    def waiting_for_elements(self):
        summary = self.job_state_summary
        if summary.all_jobs > 0 and summary.deleted + summary.error + summary.failed + summary.ok == summary.all_jobs:
            return False
        else:
            return self.collection.waiting_for_elements

    def contains_collection(self, collection_id):
        """Checks to see that the indicated collection is a member of the
        hdca by using a recursive CTE sql query to find the collection's parents
        and checking to see if any of the parents are associated with this hdca"""
        if collection_id == self.collection_id:
            # collection_id is root collection
            return True

        sa_session = object_session(self)
        DCE = DatasetCollectionElement
        HDCA = HistoryDatasetCollectionAssociation

        # non-recursive part of the cte (starting point)
        parents_cte = (
            Query(DCE.dataset_collection_id)
            .filter(or_(DCE.child_collection_id == collection_id, DCE.dataset_collection_id == collection_id))
            .cte(name="element_parents", recursive="True")
        )
        ep = aliased(parents_cte, name="ep")

        # add the recursive part of the cte expression
        dce = aliased(DCE, name="dce")
        rec = Query(dce.dataset_collection_id.label("dataset_collection_id")).filter(
            dce.child_collection_id == ep.c.dataset_collection_id
        )
        parents_cte = parents_cte.union(rec)

        # join parents to hdca, look for matching hdca_id
        hdca = aliased(HDCA, name="hdca")
        jointohdca = parents_cte.join(hdca, hdca.collection_id == parents_cte.c.dataset_collection_id)
        qry = Query(hdca.id).select_from(jointohdca).filter(hdca.id == self.id)

        results = qry.with_session(sa_session).all()
        return len(results) > 0


HistoryItem: TypeAlias = Union[HistoryDatasetAssociation, HistoryDatasetCollectionAssociation]


class LibraryDatasetCollectionAssociation(Base, DatasetCollectionInstance, RepresentById):
    """Associates a DatasetCollection with a library folder."""

    __tablename__ = "library_dataset_collection_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dataset_collection.id"), index=True)
    folder_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library_folder.id"), index=True)
    name: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    deleted: Mapped[Optional[bool]] = mapped_column(default=False)

    collection = relationship("DatasetCollection")
    folder = relationship("LibraryFolder")

    tags: Mapped[List["LibraryDatasetCollectionTagAssociation"]] = relationship(
        order_by=lambda: LibraryDatasetCollectionTagAssociation.id,
        back_populates="dataset_collection",
    )
    annotations: Mapped[List["LibraryDatasetCollectionAnnotationAssociation"]] = relationship(
        order_by=lambda: LibraryDatasetCollectionAnnotationAssociation.id,
        back_populates="dataset_collection",
    )
    ratings: Mapped[List["LibraryDatasetCollectionRatingAssociation"]] = relationship(
        order_by=lambda: LibraryDatasetCollectionRatingAssociation.id,
        back_populates="dataset_collection",
    )

    editable_keys = ("name", "deleted")

    def __init__(self, deleted=False, **kwd):
        super().__init__(**kwd)
        # Since deleted property is shared between history and dataset collections,
        # it could be on either table - some places in the code however it is convient
        # it is on instance instead of collection.
        self.deleted = deleted

    def to_dict(self, view="collection"):
        dict_value = dict(folder_id=self.folder.id, **self._base_to_dict(view=view))
        return dict_value


class DatasetCollectionElement(Base, Dictifiable, Serializable):
    """Associates a DatasetInstance (hda or ldda) with a DatasetCollection."""

    __tablename__ = "dataset_collection_element"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Parent collection id describing what collection this element belongs to.
    dataset_collection_id: Mapped[int] = mapped_column(ForeignKey("dataset_collection.id"), index=True)
    # Child defined by this association - HDA, LDDA, or another dataset association...
    hda_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history_dataset_association.id"), index=True)
    ldda_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library_dataset_dataset_association.id"), index=True)
    child_collection_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dataset_collection.id"), index=True)
    # Element index and identifier to define this parent-child relationship.
    element_index: Mapped[Optional[int]]
    element_identifier: Mapped[Optional[str]] = mapped_column(Unicode(255))

    hda = relationship(
        "HistoryDatasetAssociation",
        primaryjoin=(lambda: DatasetCollectionElement.hda_id == HistoryDatasetAssociation.id),
    )
    ldda = relationship(
        "LibraryDatasetDatasetAssociation",
        primaryjoin=(lambda: DatasetCollectionElement.ldda_id == LibraryDatasetDatasetAssociation.id),
    )
    child_collection = relationship(
        "DatasetCollection", primaryjoin=(lambda: DatasetCollectionElement.child_collection_id == DatasetCollection.id)
    )
    collection = relationship(
        "DatasetCollection",
        primaryjoin=(lambda: DatasetCollection.id == DatasetCollectionElement.dataset_collection_id),
        back_populates="elements",
    )

    # actionable dataset id needs to be available via API...
    dict_collection_visible_keys = ["id", "element_type", "element_index", "element_identifier"]
    dict_element_visible_keys = ["id", "element_type", "element_index", "element_identifier"]

    UNINITIALIZED_ELEMENT = object()

    def __init__(
        self,
        id=None,
        collection=None,
        element=None,
        element_index=None,
        element_identifier=None,
    ):
        if isinstance(element, HistoryDatasetAssociation):
            self.hda = element
        elif isinstance(element, LibraryDatasetDatasetAssociation):
            self.ldda = element
        elif isinstance(element, DatasetCollection):
            self.child_collection = element
        elif element != self.UNINITIALIZED_ELEMENT:
            raise AttributeError(f"Unknown element type provided: {type(element)}")

        self.id = id
        add_object_to_object_session(self, collection)
        self.collection = collection
        self.element_index = element_index
        self.element_identifier = element_identifier or str(element_index)

    def __strict_check_before_flush__(self):
        if self.collection.populated_optimized:
            assert self.element_object, "Dataset Collection Element without child entity detected, this is not valid"

    @property
    def element_type(self):
        if self.hda:
            return "hda"
        elif self.ldda:
            return "ldda"
        elif self.child_collection:
            # TOOD: Rename element_type to element_type.
            return "dataset_collection"
        else:
            return None

    @property
    def is_collection(self):
        return self.element_type == "dataset_collection"

    @property
    def element_object(
        self,
    ) -> Optional[Union[HistoryDatasetAssociation, LibraryDatasetDatasetAssociation, DatasetCollection]]:
        if self.hda:
            return self.hda
        elif self.ldda:
            return self.ldda
        elif self.child_collection:
            return self.child_collection
        else:
            return None

    @property
    def dataset_instance(self):
        element_object = self.element_object
        if isinstance(element_object, DatasetCollection):
            raise AttributeError("Nested collection has no associated dataset_instance.")
        return element_object

    @property
    def dataset(self):
        return self.dataset_instance.dataset

    def first_dataset_instance(self):
        element_object = self.element_object
        if isinstance(element_object, DatasetCollection):
            return element_object.dataset_instances[0]
        else:
            return element_object

    @property
    def dataset_instances(self):
        element_object = self.element_object
        if isinstance(element_object, DatasetCollection):
            return element_object.dataset_instances
        else:
            return [element_object]

    @property
    def has_deferred_data(self):
        return self.element_object.has_deferred_data

    def copy_to_collection(
        self,
        collection,
        destination=None,
        element_destination=None,
        dataset_instance_attributes=None,
        flush=True,
        minimize_copies=False,
    ):
        dataset_instance_attributes = dataset_instance_attributes or {}
        element_object = self.element_object
        if element_destination:
            if self.is_collection:
                element_object = element_object.copy(
                    destination=destination,
                    element_destination=element_destination,
                    dataset_instance_attributes=dataset_instance_attributes,
                    flush=flush,
                    minimize_copies=minimize_copies,
                )
            else:
                new_element_object = None
                if minimize_copies:
                    new_element_object = element_destination.get_dataset_by_hid(element_object.hid)
                if (
                    new_element_object
                    and new_element_object.dataset
                    and new_element_object.dataset.id == element_object.dataset_id
                ):
                    element_object = new_element_object
                else:
                    new_element_object = element_object.copy(flush=flush, copy_tags=element_object.tags)
                    for attribute, value in dataset_instance_attributes.items():
                        setattr(new_element_object, attribute, value)

                    new_element_object.visible = False
                    if destination is not None and element_object.hidden_beneath_collection_instance:
                        new_element_object.hidden_beneath_collection_instance = destination
                    # Ideally we would not need to give the following
                    # element an HID and it would exist in the history only
                    # as an element of the containing collection.
                    element_destination.stage_addition(new_element_object)
                    element_object = new_element_object

        new_element = DatasetCollectionElement(
            element=element_object,
            collection=collection,
            element_index=self.element_index,
            element_identifier=self.element_identifier,
        )
        return new_element

    def _serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            element_type=self.element_type,
            element_index=self.element_index,
            element_identifier=self.element_identifier,
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        element_obj = self.element_object
        if isinstance(element_obj, HistoryDatasetAssociation):
            rval["hda"] = element_obj.serialize(id_encoder, serialization_options, for_link=True)
        else:
            rval["child_collection"] = element_obj.serialize(id_encoder, serialization_options)
        return rval


class Event(Base, RepresentById):
    __tablename__ = "event"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    history_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    message: Mapped[Optional[str]] = mapped_column(TrimmedString(1024))
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_session.id"), index=True)
    tool_id: Mapped[Optional[str]] = mapped_column(String(255))

    history: Mapped[Optional["History"]] = relationship()
    user: Mapped[Optional["User"]] = relationship()
    galaxy_session: Mapped[Optional["GalaxySession"]] = relationship()


class GalaxySession(Base, RepresentById):
    __tablename__ = "galaxy_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    remote_host: Mapped[Optional[str]] = mapped_column(String(255))
    remote_addr: Mapped[Optional[str]] = mapped_column(String(255))
    referer: Mapped[Optional[str]] = mapped_column(TEXT)
    current_history_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history.id"))
    # unique 128 bit random number coerced to a string
    session_key: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True, unique=True)
    is_valid: Mapped[Optional[bool]] = mapped_column(default=False)
    # saves a reference to the previous session so we have a way to chain them together
    prev_session_id: Mapped[Optional[int]]
    disk_usage: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 0), index=True)
    last_action: Mapped[Optional[datetime]]
    current_history: Mapped[Optional["History"]] = relationship()
    histories: Mapped[List["GalaxySessionToHistoryAssociation"]] = relationship(
        back_populates="galaxy_session",
    )
    user: Mapped[Optional["User"]] = relationship(back_populates="galaxy_sessions")

    def __init__(self, is_valid=False, **kwd):
        super().__init__(**kwd)
        self.is_valid = is_valid
        self.last_action = self.last_action or now()

    def add_history(self, history, association=None):
        if association is None:
            self.histories.append(GalaxySessionToHistoryAssociation(self, history))
        else:
            self.histories.append(association)

    def get_disk_usage(self):
        if self.disk_usage is None:
            return 0
        return self.disk_usage

    def set_disk_usage(self, bytes):
        self.disk_usage = bytes

    total_disk_usage = property(get_disk_usage, set_disk_usage)


class GalaxySessionToHistoryAssociation(Base, RepresentById):
    __tablename__ = "galaxy_session_to_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_session.id"), index=True)
    history_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history.id"), index=True)
    galaxy_session: Mapped[Optional["GalaxySession"]] = relationship(back_populates="histories")
    history: Mapped[Optional["History"]] = relationship(back_populates="galaxy_sessions")

    def __init__(self, galaxy_session, history):
        self.galaxy_session = galaxy_session
        ensure_object_added_to_session(self, object_in_session=galaxy_session)
        add_object_to_object_session(self, history)
        self.history = history


class StoredWorkflow(Base, HasTags, Dictifiable, RepresentById, UsesCreateAndUpdateTime):
    """
    StoredWorkflow represents the root node of a tree of objects that compose a workflow, including workflow revisions, steps, and subworkflows.
    It is responsible for the metadata associated with a workflow including owner, name, published, and create/update time.

    Each time a workflow is modified a revision is created, represented by a new :class:`galaxy.model.Workflow` instance.
    See :class:`galaxy.model.Workflow` for more information
    """

    __tablename__ = "stored_workflow"
    __table_args__ = (Index("ix_stored_workflow_slug", "slug", mysql_length=200),)

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, index=True, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    latest_workflow_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow.id", use_alter=True, name="stored_workflow_latest_workflow_id_fk"), index=True
    )
    name: Mapped[Optional[str]] = mapped_column(TEXT)
    deleted: Mapped[Optional[bool]] = mapped_column(default=False)
    hidden: Mapped[Optional[bool]] = mapped_column(default=False)
    importable: Mapped[Optional[bool]] = mapped_column(default=False)
    slug: Mapped[Optional[str]] = mapped_column(TEXT)
    from_path: Mapped[Optional[str]] = mapped_column(TEXT)
    published: Mapped[Optional[bool]] = mapped_column(index=True, default=False)

    user: Mapped["User"] = relationship(
        primaryjoin=(lambda: User.id == StoredWorkflow.user_id), back_populates="stored_workflows"
    )
    workflows: Mapped[List["Workflow"]] = relationship(
        back_populates="stored_workflow",
        cascade="all, delete-orphan",
        primaryjoin=(lambda: StoredWorkflow.id == Workflow.stored_workflow_id),
        order_by=lambda: -Workflow.id,
    )
    latest_workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        post_update=True,
        primaryjoin=(lambda: StoredWorkflow.latest_workflow_id == Workflow.id),
        lazy=False,
    )
    tags: Mapped[List["StoredWorkflowTagAssociation"]] = relationship(
        order_by=lambda: StoredWorkflowTagAssociation.id,
        back_populates="stored_workflow",
    )
    owner_tags: Mapped[List["StoredWorkflowTagAssociation"]] = relationship(
        primaryjoin=(
            lambda: and_(
                StoredWorkflow.id == StoredWorkflowTagAssociation.stored_workflow_id,
                StoredWorkflow.user_id == StoredWorkflowTagAssociation.user_id,
            )
        ),
        viewonly=True,
        order_by=lambda: StoredWorkflowTagAssociation.id,
    )
    annotations: Mapped[List["StoredWorkflowAnnotationAssociation"]] = relationship(
        order_by=lambda: StoredWorkflowAnnotationAssociation.id,
        back_populates="stored_workflow",
    )
    ratings: Mapped[List["StoredWorkflowRatingAssociation"]] = relationship(
        order_by=lambda: StoredWorkflowRatingAssociation.id,
        back_populates="stored_workflow",
    )
    users_shared_with: Mapped[List["StoredWorkflowUserShareAssociation"]] = relationship(
        back_populates="stored_workflow"
    )

    average_rating = None

    # Set up proxy so that
    #   StoredWorkflow.users_shared_with
    # returns a list of users that workflow is shared with.
    users_shared_with_dot_users = association_proxy("users_shared_with", "user")

    dict_collection_visible_keys = [
        "id",
        "latest_workflow_id",
        "name",
        "create_time",
        "update_time",
        "published",
        "importable",
        "deleted",
        "hidden",
    ]
    dict_element_visible_keys = [
        "id",
        "latest_workflow_id",
        "name",
        "create_time",
        "update_time",
        "published",
        "importable",
        "deleted",
        "hidden",
    ]

    def __init__(
        self,
        user=None,
        name=None,
        slug=None,
        create_time=None,
        update_time=None,
        published=False,
        latest_workflow_id=None,
        workflow=None,
        hidden=False,
    ):
        add_object_to_object_session(self, user)
        self.user = user
        self.name = name
        self.slug = slug
        self.create_time = create_time
        self.update_time = update_time
        self.published = published
        self.latest_workflow = workflow
        self.workflows = listify(workflow)
        self.hidden = hidden

    def get_internal_version(self, version):
        if version is None:
            return self.latest_workflow
        if len(self.workflows) <= version:
            raise galaxy.exceptions.RequestParameterInvalidException("Version does not exist")
        return list(reversed(self.workflows))[version]

    def get_internal_version_by_id(self, workflow_instance_id: int):
        sa_session = object_session(self)
        assert sa_session
        workflow = sa_session.get(Workflow, workflow_instance_id)
        if not workflow:
            raise galaxy.exceptions.ObjectNotFound()
        elif workflow.stored_workflow != self:
            raise galaxy.exceptions.RequestParameterInvalidException()
        return workflow

    def version_of(self, workflow):
        for version, workflow_instance in enumerate(reversed(self.workflows)):
            if workflow_instance.id == workflow.id:
                return version
        raise KeyError("Failed to find a version of target workflow instance in stored workflow.")

    def show_in_tool_panel(self, user_id):
        sa_session = object_session(self)
        stmt = (
            select(func.count())
            .select_from(StoredWorkflowMenuEntry)
            .where(StoredWorkflowMenuEntry.stored_workflow_id == self.id)
            .where(StoredWorkflowMenuEntry.user_id == user_id)
        )
        return bool(sa_session.scalar(stmt))

    def copy_tags_from(self, target_user, source_workflow: "StoredWorkflow"):
        # Override to only copy owner tags.
        for src_swta in source_workflow.owner_tags:
            new_swta = src_swta.copy()
            new_swta.user = target_user
            self.tags.append(new_swta)

    def invocation_counts(self) -> InvocationsStateCounts:
        sa_session = object_session(self)
        assert sa_session
        stmt = (
            select(WorkflowInvocation.state, func.count(WorkflowInvocation.state))
            .select_from(StoredWorkflow)
            .join(Workflow, Workflow.stored_workflow_id == StoredWorkflow.id)
            .join(WorkflowInvocation, WorkflowInvocation.workflow_id == Workflow.id)
            .group_by(WorkflowInvocation.state)
            .where(StoredWorkflow.id == self.id)
        )
        rows = sa_session.execute(stmt).all()
        rows_as_dict = dict(r for r in rows if r[0] is not None)  # type:ignore[arg-type, var-annotated]
        return InvocationsStateCounts(rows_as_dict)

    def to_dict(self, view="collection", value_mapper=None):
        rval = super().to_dict(view=view, value_mapper=value_mapper)
        rval["latest_workflow_uuid"] = (lambda uuid: str(uuid) if self.latest_workflow.uuid else None)(
            self.latest_workflow.uuid
        )
        rval["creator_deleted"] = self.user.deleted
        return rval


class Workflow(Base, Dictifiable, RepresentById):
    """
    Workflow represents a revision of a :class:`galaxy.model.StoredWorkflow`.
    A new instance is created for each workflow revision and provides a common parent for the workflow steps.

    See :class:`galaxy.model.WorkflowStep` for more information
    """

    __tablename__ = "workflow"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    # workflows will belong to either a stored workflow or a parent/nesting workflow.
    stored_workflow_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stored_workflow.id"), index=True)
    parent_workflow_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow.id"), index=True)
    name: Mapped[Optional[str]] = mapped_column(TEXT)
    has_cycles: Mapped[Optional[bool]]
    has_errors: Mapped[Optional[bool]]
    reports_config: Mapped[Optional[bytes]] = mapped_column(JSONType)
    creator_metadata: Mapped[Optional[bytes]] = mapped_column(JSONType)
    license: Mapped[Optional[str]] = mapped_column(TEXT)
    source_metadata: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONType)
    uuid: Mapped[Optional[Union[UUID, str]]] = mapped_column(UUIDType)

    steps = relationship(
        "WorkflowStep",
        back_populates="workflow",
        primaryjoin=(lambda: Workflow.id == WorkflowStep.workflow_id),
        order_by=lambda: asc(WorkflowStep.order_index),
        cascade="all, delete-orphan",
        lazy=False,
    )
    comments: Mapped[List["WorkflowComment"]] = relationship(
        back_populates="workflow",
        primaryjoin=(lambda: Workflow.id == WorkflowComment.workflow_id),
        cascade="all, delete-orphan",
        lazy=False,
    )
    parent_workflow_steps = relationship(
        "WorkflowStep",
        primaryjoin=(lambda: Workflow.id == WorkflowStep.subworkflow_id),
        back_populates="subworkflow",
    )
    stored_workflow = relationship(
        "StoredWorkflow",
        primaryjoin=(lambda: StoredWorkflow.id == Workflow.stored_workflow_id),
        back_populates="workflows",
    )

    step_count = None

    dict_collection_visible_keys = ["name", "has_cycles", "has_errors"]
    dict_element_visible_keys = ["name", "has_cycles", "has_errors"]
    input_step_types = ["data_input", "data_collection_input", "parameter_input"]

    def __init__(self, uuid=None):
        self.user = None
        self.uuid = get_uuid(uuid)

    def has_outputs_defined(self):
        """
        Returns true or false indicating whether or not a workflow has outputs defined.
        """
        for step in self.steps:
            if step.workflow_outputs:
                return True
        return False

    def to_dict(self, view="collection", value_mapper=None):
        rval = super().to_dict(view=view, value_mapper=value_mapper)
        rval["uuid"] = (lambda uuid: str(uuid) if uuid else None)(self.uuid)
        return rval

    @property
    def steps_by_id(self):
        steps = {}
        for step in self.steps:
            step_id = step.id
            steps[step_id] = step
        return steps

    def step_by_index(self, order_index: int):
        for step in self.steps:
            if order_index == step.order_index:
                return step
        raise KeyError(f"Workflow has no step with order_index '{order_index}'")

    def step_by_label(self, label):
        for step in self.steps:
            if label == step.label:
                return step
        raise KeyError(f"Workflow has no step with label '{label}'")

    @property
    def input_steps(self):
        for step in self.steps:
            if step.type in Workflow.input_step_types:
                yield step

    @property
    def workflow_outputs(self):
        for step in self.steps:
            yield from step.workflow_outputs

    def workflow_output_for(self, output_label):
        target_output = None
        for workflow_output in self.workflow_outputs:
            if workflow_output.label == output_label:
                target_output = workflow_output
                break
        return target_output

    @property
    def workflow_output_labels(self):
        names = []
        for workflow_output in self.workflow_outputs:
            names.append(workflow_output.label)
        return names

    @property
    def top_level_workflow(self):
        """If this workflow is not attached to stored workflow directly,
        recursively grab its parents until it is the top level workflow
        which must have a stored workflow associated with it.
        """
        top_level_workflow = self
        if self.stored_workflow is None:
            # TODO: enforce this at creation...
            assert len({w.uuid for w in self.parent_workflow_steps}) == 1
            return self.parent_workflow_steps[0].workflow.top_level_workflow
        return top_level_workflow

    @property
    def top_level_stored_workflow(self):
        """If this workflow is not attached to stored workflow directly,
        recursively grab its parents until it is the top level workflow
        which must have a stored workflow associated with it and then
        grab that stored workflow.
        """
        return self.top_level_workflow.stored_workflow

    def copy(self, user: User):
        """Copy a workflow for a new StoredWorkflow object.

        Pass user if user-specific information needed.
        """
        copied_workflow = Workflow()
        copied_workflow.name = self.name
        copied_workflow.has_cycles = self.has_cycles
        copied_workflow.has_errors = self.has_errors
        copied_workflow.reports_config = self.reports_config
        copied_workflow.license = self.license
        copied_workflow.creator_metadata = self.creator_metadata

        # Map old step ids to new steps
        step_mapping = {}
        copied_steps = []
        for step in self.steps:
            copied_step = WorkflowStep()
            copied_steps.append(copied_step)
            step_mapping[step.id] = copied_step

        for old_step, new_step in zip(self.steps, copied_steps):
            old_step.copy_to(new_step, step_mapping, user=user)
        copied_workflow.steps = copied_steps

        copied_comments = [comment.copy() for comment in self.comments]
        steps_by_id = {s.order_index: s for s in copied_workflow.steps}
        comments_by_id = {c.order_index: c for c in copied_comments}

        # copy comment relationships
        for old_comment, new_comment in zip(self.comments, copied_comments):
            for step_id in [step.order_index for step in old_comment.child_steps]:
                child_step = steps_by_id.get(step_id)
                if child_step:
                    child_step.parent_comment = new_comment

            for comment_id in [comment.order_index for comment in old_comment.child_comments]:
                child_comment = comments_by_id.get(comment_id)
                if child_comment:
                    child_comment.parent_comment = new_comment

        copied_workflow.comments = copied_comments

        return copied_workflow

    @property
    def version(self):
        return self.stored_workflow.version_of(self)

    def log_str(self):
        extra = ""
        if self.stored_workflow:
            extra = f",name={self.stored_workflow.name}"
        return f"Workflow[id={self.id}{extra}]"


InputConnDictType = Dict[str, Union[Dict[str, Any], List[Dict[str, Any]]]]


class WorkflowStep(Base, RepresentById, UsesCreateAndUpdateTime):
    """
    WorkflowStep represents a tool or subworkflow, its inputs, annotations, and any outputs that are flagged as workflow outputs.

    See :class:`galaxy.model.WorkflowStepInput` and :class:`galaxy.model.WorkflowStepConnection` for more information.
    """

    __tablename__ = "workflow_step"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflow.id"), index=True)
    subworkflow_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow.id"), index=True)
    dynamic_tool_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dynamic_tool.id"), index=True)
    type: Mapped[Optional[str]] = mapped_column(String(64))
    tool_id: Mapped[Optional[str]] = mapped_column(TEXT)
    tool_version: Mapped[Optional[str]] = mapped_column(TEXT)
    tool_inputs: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType)
    tool_errors: Mapped[Optional[bytes]] = mapped_column(JSONType)
    position: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    config: Mapped[Optional[bytes]] = mapped_column(JSONType)
    order_index: Mapped[int]
    when_expression: Mapped[Optional[bytes]] = mapped_column(JSONType)
    uuid: Mapped[Optional[Union[UUID, str]]] = mapped_column(UUIDType)
    label: Mapped[Optional[str]] = mapped_column(Unicode(255))
    temp_input_connections = None
    parent_comment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_comment.id"), index=True)

    parent_comment: Mapped[Optional["WorkflowComment"]] = relationship(
        primaryjoin=(lambda: WorkflowComment.id == WorkflowStep.parent_comment_id),
        back_populates="child_steps",
    )

    subworkflow: Mapped[Optional["Workflow"]] = relationship(
        primaryjoin=(lambda: Workflow.id == WorkflowStep.subworkflow_id),
        back_populates="parent_workflow_steps",
    )
    dynamic_tool: Mapped[Optional["DynamicTool"]] = relationship(
        primaryjoin=(lambda: DynamicTool.id == WorkflowStep.dynamic_tool_id)
    )
    tags: Mapped[List["WorkflowStepTagAssociation"]] = relationship(
        order_by=lambda: WorkflowStepTagAssociation.id, back_populates="workflow_step"
    )
    annotations: Mapped[List["WorkflowStepAnnotationAssociation"]] = relationship(
        order_by=lambda: WorkflowStepAnnotationAssociation.id,
        back_populates="workflow_step",
    )
    post_job_actions = relationship("PostJobAction", back_populates="workflow_step")
    inputs = relationship("WorkflowStepInput", back_populates="workflow_step")
    workflow_outputs: Mapped[List["WorkflowOutput"]] = relationship(back_populates="workflow_step")
    output_connections: Mapped[List["WorkflowStepConnection"]] = relationship(
        primaryjoin=(lambda: WorkflowStepConnection.output_step_id == WorkflowStep.id)
    )
    workflow: Mapped["Workflow"] = relationship(
        primaryjoin=(lambda: Workflow.id == WorkflowStep.workflow_id),
        back_populates="steps",
    )

    STEP_TYPE_TO_INPUT_TYPE = {
        "data_input": "dataset",
        "data_collection_input": "dataset_collection",
        "parameter_input": "parameter",
    }
    DEFAULT_POSITION = {"left": 0, "top": 0}

    def __init__(self):
        self.uuid = uuid4()
        self._input_connections_by_name = None
        self._inputs_by_name = None
        # Injected attributes
        # TODO: code using these should be refactored to not depend on these non-persistent fields
        self.module: Optional[WorkflowModule]
        self.state: Optional[DefaultToolState]
        self.upgrade_messages: Optional[Dict]

    @reconstructor
    def init_on_load(self):
        self._input_connections_by_name = None
        self._inputs_by_name = None

    @property
    def tool_uuid(self):
        return self.dynamic_tool and self.dynamic_tool.uuid

    @property
    def is_input_type(self) -> bool:
        return bool(self.type and self.type in self.STEP_TYPE_TO_INPUT_TYPE)

    @property
    def input_type(self):
        assert self.is_input_type, "step.input_type can only be called on input step types"
        return self.STEP_TYPE_TO_INPUT_TYPE[self.type]

    def get_input_default_value(self, default_default):
        # parameter_input and the data parameters handle this slightly differently
        # unfortunately.
        if self.type == "parameter_input":
            tool_state = self.tool_inputs
            default_value = tool_state.get("default", default_default)
        else:
            default_value = default_default
            for step_input in self.inputs:
                if step_input.name == "input" and step_input.default_value_set:
                    default_value = step_input.default_value
                    break
        return default_value

    @property
    def input_optional(self):
        tool_state = self.tool_inputs
        return tool_state.get("optional") or False

    def setup_inputs_by_name(self):
        # Ensure input_connections has already been set.

        # Make connection information available on each step by input name.
        inputs_by_name: Dict[str, Any] = {}
        for step_input in self.inputs:
            input_name = step_input.name
            assert input_name not in inputs_by_name
            inputs_by_name[input_name] = step_input
        self._inputs_by_name = inputs_by_name
        return inputs_by_name

    @property
    def inputs_by_name(self):
        if self._inputs_by_name is None:
            return self.setup_inputs_by_name()
        return self._inputs_by_name

    def get_input(self, input_name):
        for step_input in self.inputs:
            if step_input.name == input_name:
                return step_input

        return None

    def get_or_add_input(self, input_name):
        step_input = self.get_input(input_name)

        if step_input is None:
            step_input = WorkflowStepInput(self)
            step_input.name = input_name
        return step_input

    def add_connection(self, input_name, output_name, output_step, input_subworkflow_step_index=None):
        step_input = self.get_or_add_input(input_name)

        conn = WorkflowStepConnection()
        conn.input_step_input = step_input
        ensure_object_added_to_session(conn, object_in_session=step_input)
        conn.output_name = output_name
        add_object_to_object_session(conn, output_step)
        conn.output_step = output_step
        if self.subworkflow:
            if input_subworkflow_step_index is not None:
                input_subworkflow_step = self.subworkflow.step_by_index(input_subworkflow_step_index)
            else:
                input_subworkflow_steps = [step for step in self.subworkflow.input_steps if step.label == input_name]
                if not input_subworkflow_steps:
                    inferred_order_index = input_name.split(":", 1)[0]
                    if inferred_order_index.isdigit():
                        input_subworkflow_steps = [self.subworkflow.step_by_index(int(inferred_order_index))]
                if len(input_subworkflow_steps) != 1:
                    # `when` expression inputs don't need to be passed into subworkflow
                    # In the absence of formal extra step inputs this seems like the best we can do.
                    # A better way to do these validations is to validate that all required subworkflow inputs
                    # are connected.
                    if input_name not in (self.when_expression or ""):
                        raise galaxy.exceptions.MessageException(
                            f"Invalid subworkflow connection at step index {self.order_index + 1}"
                        )
                    else:
                        input_subworkflow_steps = [None]
                input_subworkflow_step = input_subworkflow_steps[0]
            conn.input_subworkflow_step = input_subworkflow_step
        return conn

    @property
    def input_connections(self):
        connections = [_ for step_input in self.inputs for _ in step_input.connections]
        return connections

    @property
    def unique_workflow_outputs(self):
        # Older Galaxy workflows may have multiple WorkflowOutputs
        # per "output_name", when serving these back to the editor
        # feed only a "best" output per "output_name.""
        outputs = {}
        for workflow_output in self.workflow_outputs:
            output_name = workflow_output.output_name

            if output_name in outputs:
                found_output = outputs[output_name]
                if found_output.label is None and workflow_output.label is not None:
                    outputs[output_name] = workflow_output
            else:
                outputs[output_name] = workflow_output
        return list(outputs.values())

    @property
    def content_id(self):
        content_id = None
        if self.type == "tool":
            content_id = self.tool_id
        elif self.type == "subworkflow":
            content_id = self.subworkflow.id
        else:
            content_id = None
        return content_id

    @property
    def input_connections_by_name(self):
        if self._input_connections_by_name is None:
            self.setup_input_connections_by_name()
        return self._input_connections_by_name

    def setup_input_connections_by_name(self):
        # Ensure input_connections has already been set.

        # Make connection information available on each step by input name.
        input_connections_by_name = {}
        for conn in self.input_connections:
            input_name = conn.input_name
            if input_name not in input_connections_by_name:
                input_connections_by_name[input_name] = []
            input_connections_by_name[input_name].append(conn)
        self._input_connections_by_name = input_connections_by_name

    def create_or_update_workflow_output(self, output_name, label, uuid):
        output = self.workflow_output_for(output_name)
        if output is None:
            output = WorkflowOutput(workflow_step=self, output_name=output_name)
        if uuid is not None:
            output.uuid = uuid
        if label is not None:
            output.label = label
        return output

    def workflow_output_for(self, output_name):
        target_output = None
        for workflow_output in self.workflow_outputs:
            if workflow_output.output_name == output_name:
                target_output = workflow_output
                break
        return target_output

    def copy_to(self, copied_step: "WorkflowStep", step_mapping: Dict[int, "WorkflowStep"], user: User):
        copied_step.order_index = self.order_index
        copied_step.type = self.type
        copied_step.tool_id = self.tool_id
        copied_step.tool_version = self.tool_version
        copied_step.tool_inputs = self.tool_inputs
        copied_step.tool_errors = self.tool_errors
        copied_step.position = self.position
        copied_step.config = self.config
        copied_step.label = self.label
        copied_step.when_expression = self.when_expression
        copied_step.inputs = copy_list(self.inputs, copied_step)

        subworkflow_step_mapping = {}

        if user is not None and self.annotations:
            annotations = []
            for annotation in self.annotations:
                association = WorkflowStepAnnotationAssociation()
                association.user = user
                association.workflow_step = copied_step
                association.annotation = annotation.annotation
                annotations.append(association)
            copied_step.annotations = annotations

        if subworkflow := self.subworkflow:
            stored_subworkflow = subworkflow.stored_workflow
            if stored_subworkflow and stored_subworkflow.user == user:
                # This should be fine and reduces the number of stored subworkflows
                copied_step.subworkflow = subworkflow
                copied_subworkflow = subworkflow
            else:
                # Importing a shared workflow with a subworkflow step
                copied_subworkflow = subworkflow.copy(user=user)
                stored_workflow = StoredWorkflow(
                    user=user, name=copied_subworkflow.name, workflow=copied_subworkflow, hidden=True
                )
                copied_subworkflow.stored_workflow = stored_workflow
                copied_step.subworkflow = copied_subworkflow
            for subworkflow_step, copied_subworkflow_step in zip(subworkflow.steps, copied_subworkflow.steps):
                subworkflow_step_mapping[subworkflow_step.id] = copied_subworkflow_step

        for old_conn, new_conn in zip(self.input_connections, copied_step.input_connections):
            new_conn.input_step_input = copied_step.get_or_add_input(old_conn.input_name)
            new_conn.output_step = step_mapping[old_conn.output_step_id]
            if old_conn.input_subworkflow_step_id:
                new_conn.input_subworkflow_step = subworkflow_step_mapping[old_conn.input_subworkflow_step_id]
        for orig_pja in self.post_job_actions:
            PostJobAction(
                orig_pja.action_type,
                copied_step,
                output_name=orig_pja.output_name,
                action_arguments=orig_pja.action_arguments,
            )
        copied_step.workflow_outputs = copy_list(self.workflow_outputs, copied_step)

    def log_str(self):
        return (
            f"WorkflowStep[index={self.order_index},type={self.type},label={self.label},uuid={self.uuid},id={self.id}]"
        )

    @property
    def effective_label(self) -> Optional[str]:
        label = self.label
        if label is not None:
            return label
        elif self.is_input_type:
            tool_inputs = self.tool_inputs
            if tool_inputs is not None:
                return cast(Optional[str], tool_inputs.get("name"))
        return None

    def clear_module_extras(self):
        # the module code adds random dynamic state to the step, this
        # attempts to clear that.
        for module_attribute in ["module"]:
            try:
                delattr(self, module_attribute)
            except AttributeError:
                pass


class WorkflowStepInput(Base, RepresentById):
    __tablename__ = "workflow_step_input"
    __table_args__ = (
        Index(
            "ix_workflow_step_input_workflow_step_id_name_unique",
            "workflow_step_id",
            "name",
            unique=True,
            mysql_length={"name": 200},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id"), index=True)
    name: Mapped[Optional[str]] = mapped_column(TEXT)
    merge_type: Mapped[Optional[str]] = mapped_column(TEXT)
    scatter_type: Mapped[Optional[str]] = mapped_column(TEXT)
    value_from: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    value_from_type: Mapped[Optional[str]] = mapped_column(TEXT)
    default_value: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    default_value_set: Mapped[Optional[bool]] = mapped_column(default=False)
    runtime_value: Mapped[Optional[bool]] = mapped_column(default=False)

    workflow_step: Mapped[Optional["WorkflowStep"]] = relationship(
        back_populates="inputs",
        cascade="all",
        primaryjoin=(lambda: WorkflowStepInput.workflow_step_id == WorkflowStep.id),
    )
    connections: Mapped[List["WorkflowStepConnection"]] = relationship(
        back_populates="input_step_input",
        primaryjoin=(lambda: WorkflowStepConnection.input_step_input_id == WorkflowStepInput.id),
    )

    def __init__(self, workflow_step):
        add_object_to_object_session(self, workflow_step)
        self.workflow_step = workflow_step
        self.default_value_set = False

    def copy(self, copied_step):
        copied_step_input = WorkflowStepInput(copied_step)
        copied_step_input.name = self.name
        copied_step_input.default_value = self.default_value
        copied_step_input.default_value_set = self.default_value_set
        copied_step_input.merge_type = self.merge_type
        copied_step_input.scatter_type = self.scatter_type

        copied_step_input.connections = copy_list(self.connections)
        return copied_step_input


class WorkflowStepConnection(Base, RepresentById):
    __tablename__ = "workflow_step_connection"

    id: Mapped[int] = mapped_column(primary_key=True)
    output_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id"), index=True)
    input_step_input_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step_input.id"), index=True)
    output_name: Mapped[Optional[str]] = mapped_column(TEXT)
    input_subworkflow_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id"), index=True)

    input_step_input = relationship(
        "WorkflowStepInput",
        back_populates="connections",
        cascade="all",
        primaryjoin=(lambda: WorkflowStepConnection.input_step_input_id == WorkflowStepInput.id),
    )
    input_subworkflow_step = relationship(
        "WorkflowStep", primaryjoin=(lambda: WorkflowStepConnection.input_subworkflow_step_id == WorkflowStep.id)
    )
    output_step = relationship(
        "WorkflowStep",
        back_populates="output_connections",
        cascade="all",
        primaryjoin=(lambda: WorkflowStepConnection.output_step_id == WorkflowStep.id),
    )

    # Constant used in lieu of output_name and input_name to indicate an
    # implicit connection between two steps that is not dependent on a dataset
    # or a dataset collection. Allowing for instance data manager steps to setup
    # index data before a normal tool runs or for workflows that manage data
    # outside of Galaxy.
    NON_DATA_CONNECTION = "__NO_INPUT_OUTPUT_NAME__"

    @property
    def non_data_connection(self):
        return self.output_name == self.input_name == WorkflowStepConnection.NON_DATA_CONNECTION

    @property
    def input_name(self):
        return self.input_step_input.name

    @property
    def input_step(self) -> Optional[WorkflowStep]:
        return self.input_step_input and self.input_step_input.workflow_step

    @property
    def input_step_id(self):
        input_step = self.input_step
        return input_step and input_step.id

    def copy(self):
        # TODO: handle subworkflow ids...
        copied_connection = WorkflowStepConnection()
        copied_connection.output_name = self.output_name
        return copied_connection


class WorkflowOutput(Base, Serializable):
    __tablename__ = "workflow_output"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_step_id: Mapped[int] = mapped_column(ForeignKey("workflow_step.id"), index=True)
    output_name: Mapped[Optional[str]] = mapped_column(String(255))
    label: Mapped[Optional[str]] = mapped_column(Unicode(255))
    uuid: Mapped[Optional[Union[UUID, str]]] = mapped_column(UUIDType)
    workflow_step: Mapped["WorkflowStep"] = relationship(
        back_populates="workflow_outputs",
        primaryjoin=(lambda: WorkflowStep.id == WorkflowOutput.workflow_step_id),
    )

    def __init__(self, workflow_step, output_name=None, label=None, uuid=None):
        self.workflow_step = workflow_step
        ensure_object_added_to_session(self, object_in_session=workflow_step)
        self.output_name = output_name
        self.label = label
        self.uuid = get_uuid(uuid)

    def copy(self, copied_step):
        copied_output = WorkflowOutput(copied_step)
        copied_output.output_name = self.output_name
        copied_output.label = self.label
        return copied_output

    def _serialize(self, id_encoder, serialization_options):
        return dict_for(
            self,
            output_name=self.output_name,
            label=self.label,
            uuid=str(self.uuid),
        )


class WorkflowComment(Base, RepresentById):
    """
    WorkflowComment represents an in-editor comment which is no associated to any WorkflowStep.
    It is purely decorative, and should not influence how a workflow is ran.
    """

    __tablename__ = "workflow_comment"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_index: Mapped[Optional[int]]
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflow.id"), index=True)
    position: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    size: Mapped[Optional[bytes]] = mapped_column(JSONType)
    type: Mapped[Optional[str]] = mapped_column(String(16))
    color: Mapped[Optional[str]] = mapped_column(String(16))
    data: Mapped[Optional[bytes]] = mapped_column(JSONType)
    parent_comment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_comment.id"), index=True)

    workflow: Mapped["Workflow"] = relationship(
        primaryjoin=(lambda: Workflow.id == WorkflowComment.workflow_id),
        back_populates="comments",
    )

    child_steps = relationship(
        "WorkflowStep",
        primaryjoin=(lambda: WorkflowStep.parent_comment_id == WorkflowComment.id),
        back_populates="parent_comment",
    )

    parent_comment: Mapped[Optional["WorkflowComment"]] = relationship(
        primaryjoin=(lambda: WorkflowComment.id == WorkflowComment.parent_comment_id),
        back_populates="child_comments",
        remote_side=[id],
    )

    child_comments: Mapped[List["WorkflowComment"]] = relationship(
        primaryjoin=(lambda: WorkflowComment.parent_comment_id == WorkflowComment.id),
        back_populates="parent_comment",
    )

    def to_dict(self):
        comment_dict = {
            "id": self.order_index,
            "position": self.position,
            "size": self.size,
            "type": self.type,
            "color": self.color,
            "data": self.data,
        }

        if self.child_steps:
            comment_dict["child_steps"] = [step.order_index for step in self.child_steps]

        if self.child_comments:
            comment_dict["child_comments"] = [comment.order_index for comment in self.child_comments]

        WorkflowCommentModel(root=comment_dict)

        return comment_dict

    def from_dict(dict):
        WorkflowCommentModel(root=dict)

        comment = WorkflowComment()
        comment.order_index = dict.get("id", 0)
        comment.type = dict.get("type", "text")
        comment.position = dict.get("position", None)
        comment.size = dict.get("size", None)
        comment.color = dict.get("color", "none")
        comment.data = dict.get("data", None)
        return comment

    def copy(self):
        comment = WorkflowComment()
        comment.order_index = self.order_index
        comment.type = self.type
        comment.position = self.position
        comment.size = self.size
        comment.color = self.color
        comment.data = self.data

        return comment


class StoredWorkflowUserShareAssociation(Base, UserShareAssociation):
    __tablename__ = "stored_workflow_user_share_connection"

    id: Mapped[int] = mapped_column(primary_key=True)
    stored_workflow_id: Mapped[int] = mapped_column(ForeignKey("stored_workflow.id"), index=True, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), index=True, nullable=True)
    user: Mapped[User] = relationship()
    stored_workflow: Mapped["StoredWorkflow"] = relationship(back_populates="users_shared_with")


class StoredWorkflowMenuEntry(Base, RepresentById):
    __tablename__ = "stored_workflow_menu_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    stored_workflow_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stored_workflow.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    order_index: Mapped[Optional[int]]

    stored_workflow: Mapped[Optional["StoredWorkflow"]] = relationship()
    user: Mapped[Optional["User"]] = relationship(
        back_populates="stored_workflow_menu_entries",
        primaryjoin=(
            lambda: (StoredWorkflowMenuEntry.user_id == User.id)
            & (StoredWorkflowMenuEntry.stored_workflow_id == StoredWorkflow.id)
            & not_(StoredWorkflow.deleted)
        ),
    )


@dataclass
class InputWithRequest:
    input: Any
    request: Dict[str, Any]


@dataclass
class InputToMaterialize:
    hda: "HistoryDatasetAssociation"
    input_dataset: "WorkflowRequestToInputDatasetAssociation"


class WorkflowInvocation(Base, UsesCreateAndUpdateTime, Dictifiable, Serializable):
    __tablename__ = "workflow_invocation"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, index=True, nullable=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflow.id"), index=True)
    state: Mapped[Optional[str]] = mapped_column(TrimmedString(64), index=True)
    scheduler: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    handler: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    uuid: Mapped[Optional[Union[UUID]]] = mapped_column(UUIDType())
    history_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history.id"), index=True)

    history = relationship("History", back_populates="workflow_invocations")
    input_parameters = relationship("WorkflowRequestInputParameter", back_populates="workflow_invocation")
    step_states = relationship("WorkflowRequestStepState", back_populates="workflow_invocation")
    input_step_parameters = relationship("WorkflowRequestInputStepParameter", back_populates="workflow_invocation")
    input_datasets = relationship("WorkflowRequestToInputDatasetAssociation", back_populates="workflow_invocation")
    input_dataset_collections = relationship(
        "WorkflowRequestToInputDatasetCollectionAssociation",
        back_populates="workflow_invocation",
    )
    subworkflow_invocations = relationship(
        "WorkflowInvocationToSubworkflowInvocationAssociation",
        primaryjoin=(
            lambda: WorkflowInvocationToSubworkflowInvocationAssociation.workflow_invocation_id == WorkflowInvocation.id
        ),
        back_populates="parent_workflow_invocation",
        uselist=True,
    )
    steps = relationship(
        "WorkflowInvocationStep",
        back_populates="workflow_invocation",
        order_by=lambda: WorkflowInvocationStep.order_index,
    )
    workflow = relationship("Workflow")
    output_dataset_collections = relationship(
        "WorkflowInvocationOutputDatasetCollectionAssociation",
        back_populates="workflow_invocation",
    )
    output_datasets = relationship("WorkflowInvocationOutputDatasetAssociation", back_populates="workflow_invocation")
    output_values = relationship("WorkflowInvocationOutputValue", back_populates="workflow_invocation")
    messages = relationship("WorkflowInvocationMessage", back_populates="workflow_invocation")

    dict_collection_visible_keys = [
        "id",
        "update_time",
        "create_time",
        "workflow_id",
        "history_id",
        "uuid",
        "state",
    ]
    dict_element_visible_keys = [
        "id",
        "update_time",
        "create_time",
        "workflow_id",
        "history_id",
        "uuid",
        "state",
    ]

    states = InvocationState
    non_terminal_states = [states.NEW, states.READY]

    def create_subworkflow_invocation_for_step(self, step):
        assert step.type == "subworkflow"
        subworkflow_invocation = WorkflowInvocation()
        self.attach_subworkflow_invocation_for_step(step, subworkflow_invocation)
        return subworkflow_invocation

    def attach_subworkflow_invocation_for_step(self, step, subworkflow_invocation):
        assert step.type == "subworkflow"
        assoc = WorkflowInvocationToSubworkflowInvocationAssociation()
        assoc.workflow_invocation = self
        assoc.workflow_step = step
        add_object_to_object_session(subworkflow_invocation, self.history)
        subworkflow_invocation.history = self.history
        subworkflow_invocation.workflow = step.subworkflow
        assoc.subworkflow_invocation = subworkflow_invocation
        self.subworkflow_invocations.append(assoc)
        return assoc

    def get_subworkflow_invocation_for_step(self, step):
        assoc = self.get_subworkflow_invocation_association_for_step(step)
        return assoc.subworkflow_invocation

    def get_subworkflow_invocation_association_for_step(self, step):
        assert step.type == "subworkflow"
        assoc = None
        for subworkflow_invocation in self.subworkflow_invocations:
            if subworkflow_invocation.workflow_step == step:
                assoc = subworkflow_invocation
                break
        return assoc

    @property
    def active(self):
        """Indicates the workflow invocation is somehow active - and in
        particular valid actions may be performed on its
        WorkflowInvocationSteps.
        """
        states = WorkflowInvocation.states
        return self.state in [states.NEW, states.READY]

    def set_state(self, state: InvocationState):
        session = object_session(self)
        priority_states = (WorkflowInvocation.states.CANCELLING, WorkflowInvocation.states.CANCELLED)
        if session and self.id and state not in priority_states:
            # generate statement that will not revert CANCELLING or CANCELLED back to anything non-terminal
            session.execute(
                update(WorkflowInvocation)
                .where(
                    WorkflowInvocation.id == self.id,
                    or_(~WorkflowInvocation.state.in_(priority_states), WorkflowInvocation.state.is_(None)),
                )
                .values(state=state)
            )
        else:
            # Not bound to a session, or setting cancelling/cancelled
            self.state = state

    def cancel(self):
        if self.state not in [WorkflowInvocation.states.CANCELLING, WorkflowInvocation.states.CANCELLED]:
            # No use cancelling workflow again, for all others we may still want to be able to cancel
            # remaining tool and workflow steps
            self.state = WorkflowInvocation.states.CANCELLING
            return True
        return False

    def cancel_invocation_steps(self):
        sa_session = object_session(self)
        assert sa_session
        job_subq = (
            select(Job.id)
            .join(WorkflowInvocationStep)
            .filter(WorkflowInvocationStep.workflow_invocation_id == self.id)
            .filter(~Job.state.in_(Job.finished_states))
            .with_for_update()
        )
        sa_session.execute(update(Job).where(Job.id.in_(job_subq)).values({"state": Job.states.DELETING}))

        job_collection_subq = (
            select(Job.id)
            .join(ImplicitCollectionJobsJobAssociation)
            .join(ImplicitCollectionJobs)
            .join(
                WorkflowInvocationStep, WorkflowInvocationStep.implicit_collection_jobs_id == ImplicitCollectionJobs.id
            )
            .filter(WorkflowInvocationStep.workflow_invocation_id == self.id)
            .filter(~Job.state.in_(Job.finished_states))
            .with_for_update()
            .subquery()
        )

        sa_session.execute(
            update(Job).where(Job.id.in_(job_collection_subq.element)).values({"state": Job.states.DELETING})
        )

        for invocation in self.subworkflow_invocations:
            subworkflow_invocation = invocation.subworkflow_invocation
            cancelled = subworkflow_invocation.cancel()
            if cancelled:
                subworkflow_invocation.add_message(InvocationCancellationUserRequest(reason="user_request"))
            sa_session.add(subworkflow_invocation)
        sa_session.commit()

    def mark_cancelled(self):
        self.state = WorkflowInvocation.states.CANCELLED

    def fail(self):
        self.state = WorkflowInvocation.states.FAILED

    def step_states_by_step_id(self):
        step_states = {}
        for step_state in self.step_states:
            step_id = step_state.workflow_step_id
            step_states[step_id] = step_state
        return step_states

    def step_invocations_by_step_id(self):
        step_invocations = {}
        for invocation_step in self.steps:
            step_id = invocation_step.workflow_step_id
            assert step_id not in step_invocations
            step_invocations[step_id] = invocation_step
        return step_invocations

    def step_invocation_for_step_id(self, step_id: int) -> Optional["WorkflowInvocationStep"]:
        target_invocation_step = None
        for invocation_step in self.steps:
            if step_id == invocation_step.workflow_step_id:
                target_invocation_step = invocation_step
        return target_invocation_step

    def step_invocation_for_label(self, label):
        target_invocation_step = None
        for invocation_step in self.steps:
            if label == invocation_step.workflow_step.label:
                target_invocation_step = invocation_step
        return target_invocation_step

    @staticmethod
    def poll_unhandled_workflow_ids(sa_session):
        stmt = (
            select(WorkflowInvocation.id)
            .where(WorkflowInvocation.state == WorkflowInvocation.states.NEW)
            .where(WorkflowInvocation.handler.is_(None))
            .order_by(WorkflowInvocation.id.asc())
        )
        return list(sa_session.scalars(stmt))

    @staticmethod
    def poll_active_workflow_ids(engine, scheduler=None, handler=None):
        and_conditions = [
            or_(
                WorkflowInvocation.state == WorkflowInvocation.states.NEW,
                WorkflowInvocation.state == WorkflowInvocation.states.REQUIRES_MATERIALIZATION,
                WorkflowInvocation.state == WorkflowInvocation.states.READY,
                WorkflowInvocation.state == WorkflowInvocation.states.CANCELLING,
            ),
        ]
        if scheduler is not None:
            and_conditions.append(WorkflowInvocation.scheduler == scheduler)
        if handler is not None:
            and_conditions.append(WorkflowInvocation.handler == handler)

        stmt = select(WorkflowInvocation.id).filter(and_(*and_conditions)).order_by(WorkflowInvocation.id.asc())
        # Immediately just load all ids into memory so time slicing logic
        # is relatively intutitive.
        with engine.connect() as conn:
            return conn.scalars(stmt).all()

    def add_output(self, workflow_output, step, output_object):
        if not hasattr(output_object, "history_content_type"):
            # assuming this is a simple type, just JSON-ify it and stick in the database. In the future
            # I'd like parameter_inputs to have datasets and collections as valid parameter types so
            # dispatch on actual object and not step type.
            output_assoc = WorkflowInvocationOutputValue()
            output_assoc.workflow_invocation = self
            ensure_object_added_to_session(output_assoc, object_in_session=self)
            output_assoc.workflow_output = workflow_output
            output_assoc.workflow_step = step
            output_assoc.value = output_object
            self.output_values.append(output_assoc)
        elif output_object.history_content_type == "dataset":
            output_assoc = WorkflowInvocationOutputDatasetAssociation()
            output_assoc.workflow_invocation = self
            ensure_object_added_to_session(output_assoc, object_in_session=self)
            output_assoc.workflow_output = workflow_output
            output_assoc.workflow_step = step
            output_assoc.dataset = output_object
            self.output_datasets.append(output_assoc)
        elif output_object.history_content_type == "dataset_collection":
            output_assoc = WorkflowInvocationOutputDatasetCollectionAssociation()
            output_assoc.workflow_invocation = self
            ensure_object_added_to_session(output_assoc, object_in_session=self)
            output_assoc.workflow_output = workflow_output
            output_assoc.workflow_step = step
            output_assoc.dataset_collection = output_object
            self.output_dataset_collections.append(output_assoc)
        else:
            raise Exception("Unknown output type encountered")

    def get_output_object(self, label):
        for output_dataset_assoc in self.output_datasets:
            if output_dataset_assoc.workflow_output.label == label:
                return output_dataset_assoc.dataset
        for output_dataset_collection_assoc in self.output_dataset_collections:
            if output_dataset_collection_assoc.workflow_output.label == label:
                return output_dataset_collection_assoc.dataset_collection
        # That probably isn't good.
        workflow_output = self.workflow.workflow_output_for(label)
        if workflow_output:
            raise galaxy.exceptions.MessageException(
                f"Failed to find workflow output named [{label}], one was defined but none registered during execution."
            )
        else:
            raise galaxy.exceptions.MessageException(
                f"Failed to find workflow output named [{label}], workflow doesn't define output by that name - valid names are {self.workflow.workflow_output_labels}."
            )

    def get_input_object(self, label):
        for input_dataset_assoc in self.input_datasets:
            if input_dataset_assoc.workflow_step.label == label:
                return input_dataset_assoc.dataset
        for input_dataset_collection_assoc in self.input_dataset_collections:
            if input_dataset_collection_assoc.workflow_step.label == label:
                return input_dataset_collection_assoc.dataset_collection
        raise Exception(f"Failed to find input with label {label}")

    @property
    def output_associations(self):
        outputs = []
        for output_dataset_assoc in self.output_datasets:
            outputs.append(output_dataset_assoc)
        for output_dataset_collection_assoc in self.output_dataset_collections:
            outputs.append(output_dataset_collection_assoc)
        return outputs

    @property
    def input_associations(self):
        inputs = []
        for input_dataset_assoc in self.input_datasets:
            inputs.append(input_dataset_assoc)
        for input_dataset_collection_assoc in self.input_dataset_collections:
            inputs.append(input_dataset_collection_assoc)
        return inputs

    def inputs_requiring_materialization(self) -> List[InputToMaterialize]:
        hdas_to_materialize: List[InputToMaterialize] = []
        for input_dataset_assoc in self.input_datasets:
            request = input_dataset_assoc.request
            if request:
                deferred = request.get("deferred", False)
                if not deferred:
                    hdas_to_materialize.append(
                        InputToMaterialize(
                            input_dataset_assoc.dataset,
                            input_dataset_assoc,
                        )
                    )
        return hdas_to_materialize

    def _serialize(self, id_encoder, serialization_options):
        invocation_attrs = dict_for(self)
        invocation_attrs["state"] = self.state
        invocation_attrs["create_time"] = self.create_time.__str__()
        invocation_attrs["update_time"] = self.update_time.__str__()

        steps = []
        for step in self.steps:
            steps.append(step.serialize(id_encoder, serialization_options))
        invocation_attrs["steps"] = steps

        input_parameters = []
        for input_parameter in self.input_parameters:
            input_parameters.append(input_parameter.serialize(id_encoder, serialization_options))
        invocation_attrs["input_parameters"] = input_parameters

        step_states = []
        for step_state in self.step_states:
            step_states.append(step_state.serialize(id_encoder, serialization_options))
        invocation_attrs["step_states"] = step_states

        input_step_parameters = []
        for input_step_parameter in self.input_step_parameters:
            input_step_parameters.append(input_step_parameter.serialize(id_encoder, serialization_options))
        invocation_attrs["input_step_parameters"] = input_step_parameters

        input_datasets = []
        for input_dataset in self.input_datasets:
            input_datasets.append(input_dataset.serialize(id_encoder, serialization_options))
        invocation_attrs["input_datasets"] = input_datasets

        input_dataset_collections = []
        for input_dataset_collection in self.input_dataset_collections:
            input_dataset_collections.append(input_dataset_collection.serialize(id_encoder, serialization_options))
        invocation_attrs["input_dataset_collections"] = input_dataset_collections

        output_dataset_collections = []
        for output_dataset_collection in self.output_dataset_collections:
            output_dataset_collections.append(output_dataset_collection.serialize(id_encoder, serialization_options))
        invocation_attrs["output_dataset_collections"] = output_dataset_collections

        output_datasets = []
        for output_dataset in self.output_datasets:
            output_datasets.append(output_dataset.serialize(id_encoder, serialization_options))
        invocation_attrs["output_datasets"] = output_datasets

        output_values = []
        for output_value in self.output_values:
            output_values.append(output_value.serialize(id_encoder, serialization_options))
        invocation_attrs["output_values"] = output_values

        serialization_options.attach_identifier(id_encoder, self, invocation_attrs)
        return invocation_attrs

    def to_dict(self, view="collection", value_mapper=None, step_details=False, legacy_job_state=False):
        rval = super().to_dict(view=view, value_mapper=value_mapper)
        if rval["state"] is None:
            # bugs could result in no state being set
            rval["state"] = self.states.FAILED
        if view == "element":
            steps = []
            for step in self.steps:
                if step_details:
                    v = step.to_dict(view="element")
                else:
                    v = step.to_dict(view="collection")
                if legacy_job_state:
                    step_jobs = step.jobs
                    if step_jobs:
                        for step_job in step_jobs:
                            v_clone = v.copy()
                            v_clone["state"] = step_job.state
                            v_clone["job_id"] = step_job.id
                            steps.append(v_clone)
                    else:
                        v["state"] = None
                        steps.append(v)
                else:
                    v["implicit_collection_jobs_id"] = step.implicit_collection_jobs_id
                    steps.append(v)
            rval["steps"] = steps

            inputs = {}
            for input_item_association in self.input_datasets + self.input_dataset_collections:
                if input_item_association.history_content_type == "dataset":
                    src = "hda"
                    item = input_item_association.dataset
                elif input_item_association.history_content_type == "dataset_collection":
                    src = "hdca"
                    item = input_item_association.dataset_collection
                else:
                    # TODO: LDDAs are not implemented in workflow_request_to_input_dataset table
                    raise Exception(f"Unknown history content type '{input_item_association.history_content_type}'")
                # Should this maybe also be by label ? Would break backwards compatibility though
                inputs[str(input_item_association.workflow_step.order_index)] = {
                    "id": item.id,
                    "src": src,
                    "label": input_item_association.workflow_step.label,
                    "workflow_step_id": input_item_association.workflow_step_id,
                }

            rval["inputs"] = inputs

            input_parameters = {}
            for input_step_parameter in self.input_step_parameters:
                label = input_step_parameter.workflow_step.label
                if not label:
                    label = f"{input_step_parameter.workflow_step.order_index + 1}: Unnamed parameter"
                input_parameters[label] = {
                    "parameter_value": input_step_parameter.parameter_value,
                    "label": label,
                    "workflow_step_id": input_step_parameter.workflow_step_id,
                }
            rval["input_step_parameters"] = input_parameters

            outputs = {}
            for output_assoc in self.output_datasets:
                # TODO: does this work correctly if outputs are mapped over?
                label = output_assoc.workflow_output.label
                if not label:
                    label = f"{output_assoc.workflow_output.output_name} (Step {output_assoc.workflow_output.workflow_step.order_index + 1})"

                outputs[label] = {
                    "src": "hda",
                    "id": output_assoc.dataset_id,
                    "workflow_step_id": output_assoc.workflow_step_id,
                }

            output_collections = {}
            for output_assoc in self.output_dataset_collections:
                label = output_assoc.workflow_output.label
                if not label:
                    label = f"{output_assoc.workflow_output.output_name} (Step {output_assoc.workflow_output.workflow_step.order_index + 1})"

                output_collections[label] = {
                    "src": "hdca",
                    "id": output_assoc.dataset_collection_id,
                    "workflow_step_id": output_assoc.workflow_step_id,
                }

            rval["outputs"] = outputs
            rval["output_collections"] = output_collections

            output_values = {}
            for output_param in self.output_values:
                label = output_param.workflow_output.label
                if not label:
                    continue
                output_values[label] = output_param.value
            rval["output_values"] = output_values

        return rval

    def add_input(self, content, step_id=None, step=None):
        assert step_id is not None or step is not None

        def attach_step(request_to_content):
            if step_id is not None:
                request_to_content.workflow_step_id = step_id
            else:
                request_to_content.workflow_step = step

        request: Optional[Dict[str, Any]] = None
        if isinstance(content, InputWithRequest):
            request = content.request
            content = content.input

        history_content_type = getattr(content, "history_content_type", None)
        if history_content_type == "dataset":
            request_to_content = WorkflowRequestToInputDatasetAssociation()
            request_to_content.dataset = content
            request_to_content.request = request
            attach_step(request_to_content)
            self.input_datasets.append(request_to_content)
        elif history_content_type == "dataset_collection":
            request_to_content = WorkflowRequestToInputDatasetCollectionAssociation()
            request_to_content.dataset_collection = content
            request_to_content.request = request
            attach_step(request_to_content)
            self.input_dataset_collections.append(request_to_content)
        else:
            request_to_content = WorkflowRequestInputStepParameter()
            request_to_content.parameter_value = content
            request_to_content.request = request
            attach_step(request_to_content)
            self.input_step_parameters.append(request_to_content)

    def recover_inputs(self) -> Tuple[Dict[str, Any], str]:
        inputs = {}
        inputs_by = "name"

        have_referenced_steps_by_order_index = False

        def best_step_reference(workflow_step: "WorkflowStep") -> str:
            label = workflow_step.effective_label
            if label is not None:
                return label
            nonlocal have_referenced_steps_by_order_index
            have_referenced_steps_by_order_index = True
            return str(workflow_step.order_index)

        def ensure_step(step: Optional["WorkflowStep"]) -> "WorkflowStep":
            if step is None:
                raise galaxy.exceptions.InconsistentDatabase(
                    "workflow input found without step definition, this should not happen"
                )
            assert step
            return step

        for input_dataset_assoc in self.input_datasets:
            workflow_step = ensure_step(input_dataset_assoc.workflow_step)
            input_dataset = input_dataset_assoc.dataset
            input_index = best_step_reference(workflow_step)
            inputs[input_index] = input_dataset

        for input_dataset_collection_assoc in self.input_dataset_collections:
            workflow_step = ensure_step(input_dataset_collection_assoc.workflow_step)
            input_dataset_collection = input_dataset_collection_assoc.dataset_collection
            input_index = best_step_reference(workflow_step)
            inputs[input_index] = input_dataset_collection

        for input_step_parameter_assoc in self.input_step_parameters:
            workflow_step = ensure_step(input_step_parameter_assoc.workflow_step)
            value = input_step_parameter_assoc.parameter_value
            input_index = best_step_reference(workflow_step)
            inputs[input_index] = value

        if have_referenced_steps_by_order_index:
            inputs_by = "name|step_index"
        return inputs, inputs_by

    def add_message(self, message: "InvocationMessageUnion"):
        self.messages.append(
            WorkflowInvocationMessage(  # type:ignore[abstract]
                workflow_invocation_id=self.id,
                **message.dict(
                    exclude_unset=True,
                    exclude={
                        "history_id"
                    },  # history_id comes in through workflow_invocation and isn't persisted in database
                ),
            )
        )

    @property
    def resource_parameters(self):
        resource_type = WorkflowRequestInputParameter.types.RESOURCE_PARAMETERS
        _resource_parameters = {}
        for input_parameter in self.input_parameters:
            if input_parameter.type == resource_type:
                _resource_parameters[input_parameter.name] = input_parameter.value

        return _resource_parameters

    def has_input_for_step(self, step_id):
        for content in self.input_datasets:
            if content.workflow_step_id == step_id:
                return True
        for content in self.input_dataset_collections:
            if content.workflow_step_id == step_id:
                return True
        return False

    def set_handler(self, handler):
        self.handler = handler

    def log_str(self):
        extra = ""
        if (safe_id := getattr(self, "id", None)) is not None:
            extra += f"id={safe_id}"
        else:
            extra += "unflushed"
        return f"{self.__class__.__name__}[{extra}]"


class WorkflowInvocationToSubworkflowInvocationAssociation(Base, Dictifiable, RepresentById):
    __tablename__ = "workflow_invocation_to_subworkflow_invocation_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_invocation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_invocation.id", name="fk_wfi_swi_wfi"), index=True
    )
    subworkflow_invocation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_invocation.id", name="fk_wfi_swi_swi"), index=True
    )
    workflow_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id", name="fk_wfi_swi_ws"))

    subworkflow_invocation = relationship(
        "WorkflowInvocation",
        primaryjoin=(
            lambda: WorkflowInvocationToSubworkflowInvocationAssociation.subworkflow_invocation_id
            == WorkflowInvocation.id
        ),
        uselist=False,
    )
    workflow_step = relationship("WorkflowStep")
    parent_workflow_invocation = relationship(
        "WorkflowInvocation",
        primaryjoin=(
            lambda: WorkflowInvocationToSubworkflowInvocationAssociation.workflow_invocation_id == WorkflowInvocation.id
        ),
        back_populates="subworkflow_invocations",
        uselist=False,
    )
    dict_collection_visible_keys = ["id", "workflow_step_id", "workflow_invocation_id", "subworkflow_invocation_id"]
    dict_element_visible_keys = ["id", "workflow_step_id", "workflow_invocation_id", "subworkflow_invocation_id"]


class WorkflowInvocationMessage(Base, Dictifiable, Serializable):
    __tablename__ = "workflow_invocation_message"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_invocation_id: Mapped[int] = mapped_column(ForeignKey("workflow_invocation.id"), index=True)
    reason: Mapped[Optional[str]] = mapped_column(String(32))
    details: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    output_name: Mapped[Optional[str]] = mapped_column(String(255))
    workflow_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id"))
    dependent_workflow_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id"))
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"))
    hda_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history_dataset_association.id"))
    hdca_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history_dataset_collection_association.id"))

    workflow_invocation: Mapped["WorkflowInvocation"] = relationship(back_populates="messages", lazy=True)
    workflow_step: Mapped[Optional["WorkflowStep"]] = relationship(foreign_keys=workflow_step_id, lazy=True)
    dependent_workflow_step: Mapped[Optional["WorkflowStep"]] = relationship(
        foreign_keys=dependent_workflow_step_id, lazy=True
    )

    @property
    def workflow_step_index(self):
        return self.workflow_step and self.workflow_step.order_index

    @property
    def dependent_workflow_step_index(self):
        return self.dependent_workflow_step and self.dependent_workflow_step.order_index

    @property
    def history_id(self):
        return self.workflow_invocation.history_id


class EffectiveOutput(TypedDict):
    """An output for the sake or determining full workflow outputs.

    A workflow output might not be an effective output if it is an
    output on a subworkflow or a parent workflow that doesn't declare
    it an output.

    This is currently only used for determining object store selections.
    We don't want to capture subworkflow outputs that the user would like
    to ignore and discard as effective workflow outputs.
    """

    output_name: str
    step_id: int


class WorkflowInvocationStepObjectStores(NamedTuple):
    preferred_object_store_id: Optional[str]
    preferred_outputs_object_store_id: Optional[str]
    preferred_intermediate_object_store_id: Optional[str]
    step_effective_outputs: Optional[List["EffectiveOutput"]]

    def is_output_name_an_effective_output(self, output_name: str) -> bool:
        if self.step_effective_outputs is None:
            return True
        else:
            for effective_output in self.step_effective_outputs:
                if effective_output["output_name"] == output_name:
                    return True

            return False

    @property
    def is_split_configuration(self):
        preferred_outputs_object_store_id = self.preferred_outputs_object_store_id
        preferred_intermediate_object_store_id = self.preferred_intermediate_object_store_id
        has_typed_preferences = (
            preferred_outputs_object_store_id is not None or preferred_intermediate_object_store_id is not None
        )
        return has_typed_preferences and preferred_outputs_object_store_id != preferred_intermediate_object_store_id


class WorkflowInvocationStep(Base, Dictifiable, Serializable):
    __tablename__ = "workflow_invocation_step"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    workflow_invocation_id: Mapped[int] = mapped_column(ForeignKey("workflow_invocation.id"), index=True)
    workflow_step_id: Mapped[int] = mapped_column(ForeignKey("workflow_step.id"), index=True)
    state: Mapped[Optional[str]] = mapped_column(TrimmedString(64), index=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    implicit_collection_jobs_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("implicit_collection_jobs.id"), index=True
    )
    action: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)

    workflow_step: Mapped[WorkflowStep] = relationship("WorkflowStep")
    job: Mapped[Optional["Job"]] = relationship(back_populates="workflow_invocation_step", uselist=False)
    implicit_collection_jobs = relationship("ImplicitCollectionJobs", uselist=False)
    output_dataset_collections = relationship(
        "WorkflowInvocationStepOutputDatasetCollectionAssociation",
        back_populates="workflow_invocation_step",
    )
    output_datasets = relationship(
        "WorkflowInvocationStepOutputDatasetAssociation",
        back_populates="workflow_invocation_step",
    )
    workflow_invocation: Mapped["WorkflowInvocation"] = relationship(back_populates="steps")
    output_value = relationship(
        "WorkflowInvocationOutputValue",
        foreign_keys="[WorkflowInvocationStep.workflow_invocation_id, WorkflowInvocationStep.workflow_step_id]",
        primaryjoin=(
            lambda: and_(
                WorkflowInvocationStep.workflow_invocation_id == WorkflowInvocationOutputValue.workflow_invocation_id,
                WorkflowInvocationStep.workflow_step_id == WorkflowInvocationOutputValue.workflow_step_id,
            )
        ),
        back_populates="workflow_invocation_step",
        viewonly=True,
    )
    order_index: Mapped[int] = column_property(
        select(WorkflowStep.order_index).where(WorkflowStep.id == workflow_step_id).scalar_subquery()
    )

    dict_collection_visible_keys = [
        "id",
        "update_time",
        "job_id",
        "workflow_step_id",
        "subworkflow_invocation_id",
        "state",
        "action",
    ]
    dict_element_visible_keys = [
        "id",
        "update_time",
        "job_id",
        "workflow_step_id",
        "subworkflow_invocation_id",
        "state",
        "action",
    ]

    states = InvocationStepState

    @property
    def is_new(self):
        return self.state == self.states.NEW

    def add_output(self, output_name, output_object):
        if output_object.history_content_type == "dataset":
            output_assoc = WorkflowInvocationStepOutputDatasetAssociation()
            output_assoc.workflow_invocation_step = self
            ensure_object_added_to_session(output_assoc, object_in_session=self)
            output_assoc.dataset = output_object
            output_assoc.output_name = output_name
            self.output_datasets.append(output_assoc)
        elif output_object.history_content_type == "dataset_collection":
            output_assoc = WorkflowInvocationStepOutputDatasetCollectionAssociation()
            output_assoc.workflow_invocation_step = self
            ensure_object_added_to_session(output_assoc, object_in_session=self)
            output_assoc.dataset_collection = output_object
            output_assoc.output_name = output_name
            self.output_dataset_collections.append(output_assoc)
        else:
            raise Exception("Unknown output type encountered")

    @property
    def jobs(self):
        if self.job:
            return [self.job]
        elif self.implicit_collection_jobs:
            return self.implicit_collection_jobs.job_list
        else:
            return []

    @property
    def preferred_object_stores(self) -> WorkflowInvocationStepObjectStores:
        meta_type = WorkflowRequestInputParameter.types.META_PARAMETERS
        preferred_object_store_id = None
        preferred_outputs_object_store_id = None
        preferred_intermediate_object_store_id = None
        step_effective_outputs: Optional[List[EffectiveOutput]] = None

        workflow_invocation = self.workflow_invocation
        for input_parameter in workflow_invocation.input_parameters:
            if input_parameter.type != meta_type:
                continue
            if input_parameter.name == "preferred_object_store_id":
                preferred_object_store_id = input_parameter.value
            elif input_parameter.name == "preferred_outputs_object_store_id":
                preferred_outputs_object_store_id = input_parameter.value
            elif input_parameter.name == "preferred_intermediate_object_store_id":
                preferred_intermediate_object_store_id = input_parameter.value
            elif input_parameter.name == "effective_outputs":
                all_effective_outputs = json.loads(input_parameter.value)
                step_id = self.workflow_step_id
                step_effective_outputs = [e for e in all_effective_outputs if e["step_id"] == step_id]

        return WorkflowInvocationStepObjectStores(
            preferred_object_store_id,
            preferred_outputs_object_store_id,
            preferred_intermediate_object_store_id,
            step_effective_outputs,
        )

    def _serialize(self, id_encoder, serialization_options):
        step_attrs = dict_for(self)
        step_attrs["state"] = self.state
        step_attrs["create_time"] = self.create_time.__str__()
        step_attrs["update_time"] = self.update_time.__str__()
        step_attrs["order_index"] = self.workflow_step.order_index
        step_attrs["action"] = self.action
        if self.job:
            step_attrs["job"] = self.job.serialize(id_encoder, serialization_options, for_link=True)
        elif self.implicit_collection_jobs:
            step_attrs["implicit_collection_jobs"] = self.implicit_collection_jobs.serialize(
                id_encoder, serialization_options, for_link=True
            )

        outputs = []
        for output_dataset_assoc in self.output_datasets:
            output = dict(
                output_name=output_dataset_assoc.output_name,
            )
            dataset = output_dataset_assoc.dataset
            if dataset:
                output["dataset"] = dataset.serialize(id_encoder, serialization_options, for_link=True)
            outputs.append(output)
        step_attrs["outputs"] = outputs

        output_collections = []
        for output_dataset_collection_assoc in self.output_dataset_collections:
            output_collection = dict(
                output_name=output_dataset_collection_assoc.output_name,
            )
            dataset_collection = output_dataset_collection_assoc.dataset_collection
            if dataset_collection:
                output_collection["dataset_collection"] = dataset_collection.serialize(
                    id_encoder, serialization_options, for_link=True
                )
            output_collections.append(output_collection)
        step_attrs["output_collections"] = output_collections

        return step_attrs

    def to_dict(self, view="collection", value_mapper=None):
        rval = super().to_dict(view=view, value_mapper=value_mapper)
        rval["order_index"] = self.workflow_step.order_index
        rval["workflow_step_label"] = self.workflow_step.label
        rval["workflow_step_uuid"] = str(self.workflow_step.uuid)
        # Following no longer makes sense...
        # rval['state'] = self.job.state if self.job is not None else None
        if view == "element":
            jobs = []
            for job in self.jobs:
                jobs.append(job.to_dict())

            outputs = {}
            for output_assoc in self.output_datasets:
                name = output_assoc.output_name
                outputs[name] = {
                    "src": "hda",
                    "id": output_assoc.dataset.id,
                    "uuid": (
                        str(output_assoc.dataset.dataset.uuid)
                        if output_assoc.dataset.dataset.uuid is not None
                        else None
                    ),
                }

            output_collections = {}
            for output_assoc in self.output_dataset_collections:
                name = output_assoc.output_name
                output_collections[name] = {
                    "src": "hdca",
                    "id": output_assoc.dataset_collection.id,
                }

            rval["outputs"] = outputs
            rval["output_collections"] = output_collections
            rval["jobs"] = jobs
        return rval


class WorkflowRequestInputParameter(Base, Dictifiable, Serializable):
    """Workflow-related parameters not tied to steps or inputs."""

    __tablename__ = "workflow_request_input_parameters"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_invocation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_invocation.id", onupdate="CASCADE", ondelete="CASCADE"), index=True
    )
    name: Mapped[Optional[str]] = mapped_column(Unicode(255))
    value: Mapped[Optional[str]] = mapped_column(TEXT)
    type: Mapped[Optional[str]] = mapped_column(Unicode(255))
    workflow_invocation: Mapped[Optional["WorkflowInvocation"]] = relationship(back_populates="input_parameters")

    dict_collection_visible_keys = ["id", "name", "value", "type"]

    class types(str, Enum):
        REPLACEMENT_PARAMETERS = "replacements"
        STEP_PARAMETERS = "step"
        META_PARAMETERS = "meta"
        RESOURCE_PARAMETERS = "resource"

    def _serialize(self, id_encoder, serialization_options):
        request_input_parameter_attrs = dict_for(self)
        request_input_parameter_attrs["name"] = self.name
        request_input_parameter_attrs["value"] = self.value
        request_input_parameter_attrs["type"] = self.type
        return request_input_parameter_attrs


class WorkflowRequestStepState(Base, Dictifiable, Serializable):
    """Workflow step value parameters."""

    __tablename__ = "workflow_request_step_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_invocation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_invocation.id", onupdate="CASCADE", ondelete="CASCADE"), index=True
    )
    workflow_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id"))
    value: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    workflow_step: Mapped[Optional["WorkflowStep"]] = relationship()
    workflow_invocation: Mapped[Optional["WorkflowInvocation"]] = relationship(back_populates="step_states")

    dict_collection_visible_keys = ["id", "name", "value", "workflow_step_id"]

    def _serialize(self, id_encoder, serialization_options):
        request_step_state = dict_for(self)
        request_step_state["value"] = self.value
        request_step_state["order_index"] = self.workflow_step.order_index
        return request_step_state


class WorkflowRequestToInputDatasetAssociation(Base, Dictifiable, Serializable):
    """Workflow step input dataset parameters."""

    __tablename__ = "workflow_request_to_input_dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    workflow_invocation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_invocation.id"), index=True)
    workflow_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id"))
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history_dataset_association.id"), index=True)
    request: Mapped[Optional[Dict]] = mapped_column(JSONType)

    workflow_step: Mapped[Optional["WorkflowStep"]] = relationship()
    dataset: Mapped[Optional["HistoryDatasetAssociation"]] = relationship()
    workflow_invocation: Mapped[Optional["WorkflowInvocation"]] = relationship(back_populates="input_datasets")

    history_content_type = "dataset"
    dict_collection_visible_keys = ["id", "workflow_invocation_id", "workflow_step_id", "dataset_id", "name"]

    def _serialize(self, id_encoder, serialization_options):
        request_input_dataset_attrs = dict_for(self)
        request_input_dataset_attrs["name"] = self.name
        request_input_dataset_attrs["dataset"] = self.dataset.serialize(
            id_encoder, serialization_options, for_link=True
        )
        request_input_dataset_attrs["order_index"] = self.workflow_step.order_index
        return request_input_dataset_attrs


class WorkflowRequestToInputDatasetCollectionAssociation(Base, Dictifiable, Serializable):
    """Workflow step input dataset collection parameters."""

    __tablename__ = "workflow_request_to_input_collection_dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    workflow_invocation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_invocation.id"), index=True)
    workflow_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id"))
    dataset_collection_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("history_dataset_collection_association.id"), index=True
    )
    workflow_step: Mapped[Optional["WorkflowStep"]] = relationship()
    dataset_collection: Mapped[Optional["HistoryDatasetCollectionAssociation"]] = relationship()
    workflow_invocation: Mapped[Optional["WorkflowInvocation"]] = relationship(
        back_populates="input_dataset_collections"
    )
    request: Mapped[Optional[Dict]] = mapped_column(JSONType)

    history_content_type = "dataset_collection"
    dict_collection_visible_keys = ["id", "workflow_invocation_id", "workflow_step_id", "dataset_collection_id", "name"]

    def _serialize(self, id_encoder, serialization_options):
        request_input_collection_attrs = dict_for(self)
        request_input_collection_attrs["name"] = self.name
        request_input_collection_attrs["dataset_collection"] = self.dataset_collection.serialize(
            id_encoder, serialization_options, for_link=True
        )
        request_input_collection_attrs["order_index"] = self.workflow_step.order_index
        return request_input_collection_attrs


class WorkflowRequestInputStepParameter(Base, Dictifiable, Serializable):
    """Workflow step parameter inputs."""

    __tablename__ = "workflow_request_input_step_parameter"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_invocation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_invocation.id"), index=True)
    workflow_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id"))
    parameter_value: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    request: Mapped[Optional[Dict]] = mapped_column(JSONType)

    workflow_step: Mapped[Optional["WorkflowStep"]] = relationship()
    workflow_invocation: Mapped[Optional["WorkflowInvocation"]] = relationship(back_populates="input_step_parameters")

    dict_collection_visible_keys = ["id", "workflow_invocation_id", "workflow_step_id", "parameter_value"]

    def _serialize(self, id_encoder, serialization_options):
        request_input_step_parameter_attrs = dict_for(self)
        request_input_step_parameter_attrs["parameter_value"] = self.parameter_value
        request_input_step_parameter_attrs["order_index"] = self.workflow_step.order_index
        return request_input_step_parameter_attrs


class WorkflowInvocationOutputDatasetAssociation(Base, Dictifiable, Serializable):
    """Represents links to output datasets for the workflow."""

    __tablename__ = "workflow_invocation_output_dataset_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_invocation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_invocation.id"), index=True)
    workflow_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id"), index=True)
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history_dataset_association.id"), index=True)
    workflow_output_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_output.id"), index=True)
    workflow_invocation: Mapped[Optional["WorkflowInvocation"]] = relationship(back_populates="output_datasets")
    workflow_step: Mapped[Optional["WorkflowStep"]] = relationship()
    dataset: Mapped[Optional["HistoryDatasetAssociation"]] = relationship()
    workflow_output: Mapped[Optional["WorkflowOutput"]] = relationship()

    history_content_type = "dataset"
    dict_collection_visible_keys = ["id", "workflow_invocation_id", "workflow_step_id", "dataset_id", "name"]

    def _serialize(self, id_encoder, serialization_options):
        output_dataset_attrs = dict_for(self)
        output_dataset_attrs["dataset"] = self.dataset.serialize(id_encoder, serialization_options, for_link=True)
        output_dataset_attrs["order_index"] = self.workflow_step.order_index
        output_dataset_attrs["workflow_output"] = self.workflow_output.serialize(id_encoder, serialization_options)
        return output_dataset_attrs


class WorkflowInvocationOutputDatasetCollectionAssociation(Base, Dictifiable, Serializable):
    """Represents links to output dataset collections for the workflow."""

    __tablename__ = "workflow_invocation_output_dataset_collection_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_invocation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_invocation.id", name="fk_wiodca_wii"), index=True
    )
    workflow_step_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_step.id", name="fk_wiodca_wsi"), index=True
    )
    dataset_collection_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("history_dataset_collection_association.id", name="fk_wiodca_dci"), index=True
    )
    workflow_output_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_output.id", name="fk_wiodca_woi"), index=True
    )

    workflow_invocation: Mapped[Optional["WorkflowInvocation"]] = relationship(
        back_populates="output_dataset_collections"
    )
    workflow_step: Mapped[Optional["WorkflowStep"]] = relationship()
    dataset_collection: Mapped[Optional["HistoryDatasetCollectionAssociation"]] = relationship()
    workflow_output: Mapped[Optional["WorkflowOutput"]] = relationship()

    history_content_type = "dataset_collection"
    dict_collection_visible_keys = ["id", "workflow_invocation_id", "workflow_step_id", "dataset_collection_id", "name"]

    def _serialize(self, id_encoder, serialization_options):
        output_collection_attrs = dict_for(self)
        output_collection_attrs["dataset_collection"] = self.dataset_collection.serialize(
            id_encoder, serialization_options, for_link=True
        )
        output_collection_attrs["order_index"] = self.workflow_step.order_index
        output_collection_attrs["workflow_output"] = self.workflow_output.serialize(id_encoder, serialization_options)
        return output_collection_attrs


class WorkflowInvocationOutputValue(Base, Dictifiable, Serializable):
    """Represents a link to a specified or computed workflow parameter."""

    __tablename__ = "workflow_invocation_output_value"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_invocation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_invocation.id"), index=True)
    workflow_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_step.id"))
    workflow_output_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_output.id"), index=True)
    value: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)

    workflow_invocation: Mapped[Optional["WorkflowInvocation"]] = relationship(back_populates="output_values")

    workflow_invocation_step: Mapped[Optional["WorkflowInvocationStep"]] = relationship(
        foreign_keys="[WorkflowInvocationStep.workflow_invocation_id, WorkflowInvocationStep.workflow_step_id]",
        primaryjoin=(
            lambda: and_(
                WorkflowInvocationStep.workflow_invocation_id == WorkflowInvocationOutputValue.workflow_invocation_id,
                WorkflowInvocationStep.workflow_step_id == WorkflowInvocationOutputValue.workflow_step_id,
            )
        ),
        back_populates="output_value",
        viewonly=True,
    )

    workflow_step: Mapped[Optional["WorkflowStep"]] = relationship()
    workflow_output: Mapped[Optional["WorkflowOutput"]] = relationship()

    dict_collection_visible_keys = ["id", "workflow_invocation_id", "workflow_step_id", "value"]

    def _serialize(self, id_encoder, serialization_options):
        output_value_attrs = dict_for(self)
        output_value_attrs["value"] = self.value
        output_value_attrs["order_index"] = self.workflow_step.order_index
        output_value_attrs["workflow_output"] = self.workflow_output.serialize(id_encoder, serialization_options)
        return output_value_attrs


class WorkflowInvocationStepOutputDatasetAssociation(Base, Dictifiable, RepresentById):
    """Represents links to output datasets for the workflow."""

    __tablename__ = "workflow_invocation_step_output_dataset_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_invocation_step_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_invocation_step.id"), index=True
    )
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history_dataset_association.id"), index=True)
    output_name: Mapped[Optional[str]] = mapped_column(String(255))
    workflow_invocation_step: Mapped[Optional["WorkflowInvocationStep"]] = relationship(
        back_populates="output_datasets"
    )
    dataset: Mapped[Optional["HistoryDatasetAssociation"]] = relationship()

    dict_collection_visible_keys = ["id", "workflow_invocation_step_id", "dataset_id", "output_name"]


class WorkflowInvocationStepOutputDatasetCollectionAssociation(Base, Dictifiable, RepresentById):
    """Represents links to output dataset collections for the workflow."""

    __tablename__ = "workflow_invocation_step_output_dataset_collection_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_invocation_step_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_invocation_step.id", name="fk_wisodca_wisi"), index=True
    )
    workflow_step_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_step.id", name="fk_wisodca_wsi"), index=True
    )
    dataset_collection_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("history_dataset_collection_association.id", name="fk_wisodca_dci"), index=True
    )
    output_name: Mapped[Optional[str]] = mapped_column(String(255))

    workflow_invocation_step: Mapped[Optional["WorkflowInvocationStep"]] = relationship(
        back_populates="output_dataset_collections"
    )
    dataset_collection: Mapped[Optional["HistoryDatasetCollectionAssociation"]] = relationship()

    dict_collection_visible_keys = ["id", "workflow_invocation_step_id", "dataset_collection_id", "output_name"]


class MetadataFile(Base, StorableObject, Serializable):
    __tablename__ = "metadata_file"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(TEXT)
    hda_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history_dataset_association.id"), index=True)
    lda_id: Mapped[Optional[int]] = mapped_column(ForeignKey("library_dataset_dataset_association.id"), index=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(index=True, default=now, onupdate=now, nullable=True)
    object_store_id: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    uuid: Mapped[Optional[Union[UUID, str]]] = mapped_column(UUIDType(), index=True)
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    purged: Mapped[Optional[bool]] = mapped_column(index=True, default=False)

    history_dataset: Mapped[Optional["HistoryDatasetAssociation"]] = relationship()
    library_dataset: Mapped[Optional["LibraryDatasetDatasetAssociation"]] = relationship()

    def __init__(self, dataset=None, name=None, uuid=None):
        self.uuid = get_uuid(uuid)
        if isinstance(dataset, HistoryDatasetAssociation):
            self.history_dataset = dataset
        elif isinstance(dataset, LibraryDatasetDatasetAssociation):
            self.library_dataset = dataset
        self.name = name

    @property
    def dataset(self) -> Optional["DatasetInstance"]:
        da = self.history_dataset or self.library_dataset
        return da and da.dataset

    def update_from_file(self, file_name):
        if not self.dataset:
            raise Exception("Attempted to write MetadataFile, but no DatasetAssociation set")
        if not self.dataset.purged:
            self.dataset.object_store.update_from_file(
                self,
                file_name=file_name,
                extra_dir="_metadata_files",
                extra_dir_at_root=True,
                alt_name=os.path.basename(self.get_file_name()),
            )

    def get_file_name(self, sync_cache: bool = True) -> str:
        # Ensure the directory structure and the metadata file object exist
        try:
            da = self.history_dataset or self.library_dataset
            assert da is not None
            if self.object_store_id is None:
                self.object_store_id = da.dataset.object_store_id
            object_store = da.dataset.object_store
            store_by = object_store.get_store_by(da.dataset)
            if store_by == "id" and self.id is None:
                self.flush()  # type:ignore[unreachable]
            identifier = getattr(self, store_by)
            alt_name = f"metadata_{identifier}.dat"
            if not object_store.exists(self, extra_dir="_metadata_files", extra_dir_at_root=True, alt_name=alt_name):
                object_store.create(self, extra_dir="_metadata_files", extra_dir_at_root=True, alt_name=alt_name)
            path = object_store.get_filename(
                self, extra_dir="_metadata_files", extra_dir_at_root=True, alt_name=alt_name, sync_cache=sync_cache
            )
            return path
        except (AssertionError, AttributeError):
            assert (
                self.id is not None
            ), "ID must be set before MetadataFile used without an HDA/LDDA (commit the object)"
            # In case we're not working with the history_dataset
            path = os.path.join(Dataset.file_path, "_metadata_files", *directory_hash_id(self.id))
            # Create directory if it does not exist
            try:
                os.makedirs(path)
            except OSError as e:
                # File Exists is okay, otherwise reraise
                if e.errno != errno.EEXIST:
                    raise
            # Return filename inside hashed directory
            return os.path.abspath(os.path.join(path, f"metadata_{self.id}.dat"))

    def _serialize(self, id_encoder, serialization_options):
        as_dict = dict_for(self)
        serialization_options.attach_identifier(id_encoder, self, as_dict)
        as_dict["uuid"] = str(self.uuid or "") or None
        return as_dict


class FormDefinition(Base, Dictifiable, RepresentById):
    __tablename__ = "form_definition"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(default=now)
    update_time: Mapped[Optional[datetime]] = mapped_column(default=now, onupdate=now)
    name: Mapped[str] = mapped_column(TrimmedString(255))
    desc: Mapped[Optional[str]] = mapped_column(TEXT)
    form_definition_current_id: Mapped[int] = mapped_column(
        ForeignKey("form_definition_current.id", use_alter=True), index=True
    )
    fields: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    type: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    layout: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    form_definition_current: Mapped["FormDefinitionCurrent"] = relationship(
        back_populates="forms",
        primaryjoin=(lambda: FormDefinitionCurrent.id == FormDefinition.form_definition_current_id),
    )

    # The following form_builder classes are supported by the FormDefinition class.
    supported_field_types = [
        AddressField,
        CheckboxField,
        PasswordField,
        SelectField,
        TextArea,
        TextField,
        WorkflowField,
        WorkflowMappingField,
        HistoryField,
    ]

    class types(str, Enum):
        USER_INFO = "User Information"

    dict_collection_visible_keys = ["id", "name"]
    dict_element_visible_keys = ["id", "name", "desc", "form_definition_current_id", "fields", "layout"]

    def populate(self, user=None, values=None, security=None):
        values = values or {}
        form_def = {"id": security.encode_id(self.id) if security else self.id, "name": self.name, "inputs": []}
        for field in self.fields:
            FieldClass = (
                {
                    "AddressField": AddressField,
                    "CheckboxField": CheckboxField,
                    "HistoryField": HistoryField,
                    "PasswordField": PasswordField,
                    "SelectField": SelectField,
                    "TextArea": TextArea,
                    "TextField": TextField,
                    "WorkflowField": WorkflowField,
                }
            ).get(field["type"], TextField)
            form_def["inputs"].append(
                FieldClass(
                    user=user, value=values.get(field["name"], field.get("default")), security=security, **field
                ).to_dict()
            )
        return form_def

    def grid_fields(self, grid_index):
        # Returns a dictionary whose keys are integers corresponding to field positions
        # on the grid and whose values are the field.
        gridfields = {}
        for i, f in enumerate(self.fields):
            if str(f["layout"]) == str(grid_index):
                gridfields[i] = f
        return gridfields


class FormDefinitionCurrent(Base, RepresentById):
    __tablename__ = "form_definition_current"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    latest_form_id: Mapped[Optional[int]] = mapped_column(ForeignKey("form_definition.id"), index=True)
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    forms: Mapped[List["FormDefinition"]] = relationship(
        back_populates="form_definition_current",
        cascade="all, delete-orphan",
        primaryjoin=(lambda: FormDefinitionCurrent.id == FormDefinition.form_definition_current_id),
    )
    latest_form: Mapped[Optional["FormDefinition"]] = relationship(
        post_update=True,
        primaryjoin=(lambda: FormDefinitionCurrent.latest_form_id == FormDefinition.id),
    )

    def __init__(self, form_definition=None):
        self.latest_form = form_definition


class FormValues(Base, RepresentById):
    __tablename__ = "form_values"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    form_definition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("form_definition.id"), index=True)
    content: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    form_definition: Mapped[Optional["FormDefinition"]] = relationship(
        primaryjoin=(lambda: FormValues.form_definition_id == FormDefinition.id)
    )

    def __init__(self, form_def=None, content=None):
        self.form_definition = form_def
        self.content = content


class UserAddress(Base, RepresentById):
    __tablename__ = "user_address"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    desc: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    name: Mapped[str] = mapped_column(TrimmedString(255))
    institution: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    address: Mapped[str] = mapped_column(TrimmedString(255))
    city: Mapped[str] = mapped_column(TrimmedString(255))
    state: Mapped[str] = mapped_column(TrimmedString(255))
    postal_code: Mapped[str] = mapped_column(TrimmedString(255))
    country: Mapped[str] = mapped_column(TrimmedString(255))
    phone: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    purged: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    # `desc` needs to be fully qualified because it is shadowed by `desc` Column defined above
    # TODO: db migration to rename column, then use `desc`
    user: Mapped[Optional["User"]] = relationship(back_populates="addresses", order_by=sqlalchemy.desc("update_time"))

    def to_dict(self, trans):
        return {
            "id": trans.security.encode_id(self.id),
            "name": sanitize_html(self.name),
            "desc": sanitize_html(self.desc),
            "institution": sanitize_html(self.institution),
            "address": sanitize_html(self.address),
            "city": sanitize_html(self.city),
            "state": sanitize_html(self.state),
            "postal_code": sanitize_html(self.postal_code),
            "country": sanitize_html(self.country),
            "phone": sanitize_html(self.phone),
        }


class PSAAssociation(Base, AssociationMixin, RepresentById):
    __tablename__ = "psa_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_url: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    handle: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    secret: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    issued: Mapped[Optional[int]]
    lifetime: Mapped[Optional[int]]
    assoc_type: Mapped[Optional[str]] = mapped_column(VARCHAR(64))

    # This static property is set at: galaxy.authnz.psa_authnz.PSAAuthnz
    sa_session = None

    def save(self):
        self.sa_session.add(self)
        with transaction(self.sa_session):
            self.sa_session.commit()

    @classmethod
    def store(cls, server_url, association):
        """
        Create an Association instance
        (Required by social_core.storage.AssociationMixin interface)
        """

        def get_or_create():
            stmt = select(PSAAssociation).filter_by(server_url=server_url, handle=association.handle).limit(1)
            assoc = cls.sa_session.scalars(stmt).first()
            return assoc or cls(server_url=server_url, handle=association.handle)

        assoc = get_or_create()
        assoc.secret = base64.encodebytes(association.secret).decode()
        assoc.issued = association.issued
        assoc.lifetime = association.lifetime
        assoc.assoc_type = association.assoc_type
        cls.sa_session.add(assoc)
        with transaction(cls.sa_session):
            cls.sa_session.commit()

    @classmethod
    def get(cls, *args, **kwargs):
        """
        Get an Association instance
        (Required by social_core.storage.AssociationMixin interface)
        """
        stmt = select(PSAAssociation).filter_by(*args, **kwargs)
        return cls.sa_session.scalars(stmt).all()

    @classmethod
    def remove(cls, ids_to_delete):
        """
        Remove an Association instance
        (Required by social_core.storage.AssociationMixin interface)
        """
        stmt = (
            delete(PSAAssociation)
            .where(PSAAssociation.id.in_(ids_to_delete))
            .execution_options(synchronize_session="fetch")
        )
        PSAAssociation.sa_session.execute(stmt)


class PSACode(Base, CodeMixin, RepresentById):
    __tablename__ = "psa_code"
    __table_args__ = (UniqueConstraint("code", "email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(VARCHAR(200))
    code: Mapped[Optional[str]] = mapped_column(VARCHAR(32))

    # This static property is set at: galaxy.authnz.psa_authnz.PSAAuthnz
    sa_session = None

    def __init__(self, email, code):
        self.email = email
        self.code = code

    def save(self):
        self.sa_session.add(self)
        with transaction(self.sa_session):
            self.sa_session.commit()

    @classmethod
    def get_code(cls, code):
        """
        (Required by social_core.storage.CodeMixin interface)
        """
        stmt = select(PSACode).where(PSACode.code == code).limit(1)
        return cls.sa_session.scalars(stmt).first()


class PSANonce(Base, NonceMixin, RepresentById):
    __tablename__ = "psa_nonce"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_url: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    timestamp: Mapped[Optional[int]]
    salt: Mapped[Optional[str]] = mapped_column(VARCHAR(40))

    # This static property is set at: galaxy.authnz.psa_authnz.PSAAuthnz
    sa_session = None

    def __init__(self, server_url, timestamp, salt):
        self.server_url = server_url
        self.timestamp = timestamp
        self.salt = salt

    def save(self):
        self.sa_session.add(self)
        with transaction(self.sa_session):
            self.sa_session.commit()

    @classmethod
    def use(cls, server_url, timestamp, salt):
        """
        Create a Nonce instance
        (Required by social_core.storage.NonceMixin interface)
        """
        try:
            stmt = select(PSANonce).where(server_url=server_url, timestamp=timestamp, salt=salt).limit(1)
            return cls.sa_session.scalars(stmt).first()
        except IndexError:
            instance = cls(server_url=server_url, timestamp=timestamp, salt=salt)
            cls.sa_session.add(instance)
            with transaction(cls.sa_session):
                cls.sa_session.commit()
            return instance


class PSAPartial(Base, PartialMixin, RepresentById):
    __tablename__ = "psa_partial"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[Optional[str]] = mapped_column(VARCHAR(32))
    data: Mapped[Optional[str]] = mapped_column(TEXT)
    next_step: Mapped[Optional[int]]
    backend: Mapped[Optional[str]] = mapped_column(VARCHAR(32))

    # This static property is set at: galaxy.authnz.psa_authnz.PSAAuthnz
    sa_session = None

    def __init__(self, token, data, next_step, backend):
        self.token = token
        self.data = data
        self.next_step = next_step
        self.backend = backend

    def save(self):
        self.sa_session.add(self)
        with transaction(self.sa_session):
            self.sa_session.commit()

    @classmethod
    def load(cls, token):
        """
        (Required by social_core.storage.PartialMixin interface)
        """
        stmt = select(PSAPartial).where(PSAPartial.token == token).limit(1)
        return cls.sa_session.scalars(stmt).first()

    @classmethod
    def destroy(cls, token):
        """
        (Required by social_core.storage.PartialMixin interface)
        """
        if partial := cls.load(token):
            session = cls.sa_session
            session.execute(delete(partial))
            with transaction(session):
                session.commit()


class UserAuthnzToken(Base, UserMixin, RepresentById):
    __tablename__ = "oidc_user_authnz_tokens"
    __table_args__ = (UniqueConstraint("provider", "uid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    uid: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    provider: Mapped[Optional[str]] = mapped_column(VARCHAR(32))
    extra_data: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    lifetime: Mapped[Optional[int]]
    assoc_type: Mapped[Optional[str]] = mapped_column(VARCHAR(64))
    user: Mapped[Optional["User"]] = relationship(back_populates="social_auth")

    # This static property is set at: galaxy.authnz.psa_authnz.PSAAuthnz
    sa_session = None

    def __init__(self, provider, uid, extra_data=None, lifetime=None, assoc_type=None, user=None):
        self.provider = provider
        self.uid = uid
        self.user_id = user.id
        self.extra_data = extra_data
        self.lifetime = lifetime
        self.assoc_type = assoc_type

    def get_id_token(self, strategy):
        if self.access_token_expired():
            # Access and ID tokens have same expiration time;
            # hence, if one is expired, the other is expired too.
            self.refresh_token(strategy)
        return self.extra_data.get("id_token", None) if self.extra_data is not None else None

    def set_extra_data(self, extra_data=None):
        if super().set_extra_data(extra_data):
            self.sa_session.add(self)
            with transaction(self.sa_session):
                self.sa_session.commit()

    def save(self):
        self.sa_session.add(self)
        with transaction(self.sa_session):
            self.sa_session.commit()

    @classmethod
    def changed(cls, user):
        """
        The given user instance is ready to be saved
        (Required by social_core.storage.UserMixin interface)
        """
        cls.sa_session.add(user)
        with transaction(cls.sa_session):
            cls.sa_session.commit()

    @classmethod
    def get_username(cls, user):
        """
        Return the username for given user
        (Required by social_core.storage.UserMixin interface)
        """
        return getattr(user, "username", None)

    @classmethod
    def user_model(cls):
        """
        Return the user model
        (Required by social_core.storage.UserMixin interface)
        """
        return User

    @classmethod
    def username_max_length(cls):
        """
        Return the max length for username
        (Required by social_core.storage.UserMixin interface)
        """
        # Note: This is the maximum field length set for the username column of the galaxy_user table.
        # A better alternative is to retrieve this number from the table, instead of this const value.
        return 255

    @classmethod
    def user_exists(cls, *args, **kwargs):
        """
        Return True/False if a User instance exists with the given arguments.
        Arguments are directly passed to filter() manager method.
        (Required by social_core.storage.UserMixin interface)
        """
        stmt_user = select(User).filter_by(*args, **kwargs)
        stmt_count = select(func.count()).select_from(stmt_user)
        return cls.sa_session.scalar(stmt_count) > 0

    @classmethod
    def create_user(cls, *args, **kwargs):
        """
        This is used by PSA authnz, do not use directly.
        Prefer using the user manager.
        (Required by social_core.storage.UserMixin interface)
        """
        model = cls.user_model()
        instance = model(*args, **kwargs)
        if cls.get_users_by_email(instance.email):
            raise Exception(f"User with this email '{instance.email}' already exists.")
        instance.set_random_password()
        cls.sa_session.add(instance)
        with transaction(cls.sa_session):
            cls.sa_session.commit()
        return instance

    @classmethod
    def get_user(cls, pk):
        """
        Return user instance for given id
        (Required by social_core.storage.UserMixin interface)
        """
        return cls.sa_session.get(User, pk)

    @classmethod
    def get_users_by_email(cls, email):
        """
        Return users instances for given email address
        (Required by social_core.storage.UserMixin interface)
        """
        stmt = select(User).where(func.lower(User.email) == email.lower())
        return cls.sa_session.scalars(stmt).all()

    @classmethod
    def get_social_auth(cls, provider, uid):
        """
        Return UserSocialAuth for given provider and uid
        (Required by social_core.storage.UserMixin interface)
        """
        uid = str(uid)
        stmt = select(cls).filter_by(provider=provider, uid=uid).limit(1)
        return cls.sa_session.scalars(stmt).first()

    @classmethod
    def get_social_auth_for_user(cls, user, provider=None, id=None):
        """
        Return all the UserSocialAuth instances for given user
        (Required by social_core.storage.UserMixin interface)
        """
        stmt = select(cls).filter_by(user_id=user.id)
        if provider:
            stmt = stmt.filter_by(provider=provider)
        if id:
            stmt = stmt.filter_by(id=id)
        return cls.sa_session.scalars(stmt).all()

    @classmethod
    def create_social_auth(cls, user, uid, provider):
        """
        Create a UserSocialAuth instance for given user
        (Required by social_core.storage.UserMixin interface)
        """
        uid = str(uid)
        instance = cls(user=user, uid=uid, provider=provider)
        cls.sa_session.add(instance)
        with transaction(cls.sa_session):
            cls.sa_session.commit()
        return instance


class CustosAuthnzToken(Base, RepresentById):
    __tablename__ = "custos_authnz_token"
    __table_args__ = (
        UniqueConstraint("user_id", "external_user_id", "provider"),
        UniqueConstraint("external_user_id", "provider"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), nullable=True)
    external_user_id: Mapped[Optional[str]] = mapped_column(String(255))
    provider: Mapped[Optional[str]] = mapped_column(String(255))
    access_token: Mapped[Optional[str]] = mapped_column(Text)
    id_token: Mapped[Optional[str]] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    expiration_time: Mapped[datetime] = mapped_column(nullable=True)
    refresh_expiration_time: Mapped[datetime] = mapped_column(nullable=True)
    user: Mapped["User"] = relationship("User", back_populates="custos_auth")


class Page(Base, HasTags, Dictifiable, RepresentById, UsesCreateAndUpdateTime):
    __tablename__ = "page"
    __table_args__ = (Index("ix_page_slug", "slug", mysql_length=200),)

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    latest_revision_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("page_revision.id", use_alter=True, name="page_latest_revision_id_fk"), index=True
    )
    title: Mapped[Optional[str]] = mapped_column(TEXT)
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    importable: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    slug: Mapped[Optional[str]] = mapped_column(TEXT)
    published: Mapped[Optional[bool]] = mapped_column(index=True, default=False)
    user: Mapped["User"] = relationship()
    revisions: Mapped[List["PageRevision"]] = relationship(
        cascade="all, delete-orphan",
        primaryjoin=(lambda: Page.id == PageRevision.page_id),
        back_populates="page",
    )
    latest_revision: Mapped[Optional["PageRevision"]] = relationship(
        post_update=True,
        primaryjoin=(lambda: Page.latest_revision_id == PageRevision.id),
        lazy=False,
    )
    tags: Mapped[List["PageTagAssociation"]] = relationship(
        order_by=lambda: PageTagAssociation.id, back_populates="page"
    )
    annotations: Mapped[List["PageAnnotationAssociation"]] = relationship(
        order_by=lambda: PageAnnotationAssociation.id, back_populates="page"
    )
    ratings: Mapped[List["PageRatingAssociation"]] = relationship(
        order_by=lambda: PageRatingAssociation.id,
        back_populates="page",
    )
    users_shared_with: Mapped[List["PageUserShareAssociation"]] = relationship(back_populates="page")

    # Set up proxy so that
    #   Page.users_shared_with
    # returns a list of users that page is shared with.
    users_shared_with_dot_users = association_proxy("users_shared_with", "user")

    dict_element_visible_keys = [
        "id",
        "title",
        "latest_revision_id",
        "slug",
        "published",
        "importable",
        "deleted",
        "username",
        "email_hash",
        "author_deleted",
        "create_time",
        "update_time",
    ]

    def to_dict(self, view="element"):
        rval = super().to_dict(view=view)
        if "importable" in rval and rval["importable"] is None:
            # pages created prior to 2011 might not have importable field
            # probably not worth creating a migration to fix that
            rval["importable"] = False
        rev = []
        for a in self.revisions:
            rev.append(a.id)
        rval["revision_ids"] = rev
        return rval

    # username needed for slug generation
    @property
    def username(self):
        return self.user.username

    # email needed for hash generation
    @property
    def email_hash(self):
        return md5_hash_str(self.user.email)

    # needed to determine how to display page details
    @property
    def author_deleted(self):
        return self.user.deleted


class PageRevision(Base, Dictifiable, RepresentById):
    __tablename__ = "page_revision"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("page.id"), index=True)
    title: Mapped[Optional[str]] = mapped_column(TEXT)
    content: Mapped[Optional[str]] = mapped_column(TEXT)
    content_format: Mapped[Optional[str]] = mapped_column(TrimmedString(32))
    page: Mapped["Page"] = relationship(primaryjoin=(lambda: Page.id == PageRevision.page_id))
    DEFAULT_CONTENT_FORMAT = "html"
    dict_element_visible_keys = ["id", "page_id", "title", "content", "content_format"]

    def __init__(self):
        self.content_format = PageRevision.DEFAULT_CONTENT_FORMAT

    def to_dict(self, view="element"):
        rval = super().to_dict(view=view)
        rval["create_time"] = self.create_time.isoformat()
        rval["update_time"] = self.update_time.isoformat()
        return rval


class PageUserShareAssociation(Base, UserShareAssociation):
    __tablename__ = "page_user_share_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("page.id"), index=True, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), index=True, nullable=True)
    user: Mapped[User] = relationship()
    page: Mapped["Page"] = relationship(back_populates="users_shared_with")


class Visualization(Base, HasTags, Dictifiable, RepresentById, UsesCreateAndUpdateTime):
    __tablename__ = "visualization"
    __table_args__ = (
        Index("ix_visualization_dbkey", "dbkey", mysql_length=200),
        Index("ix_visualization_slug", "slug", mysql_length=200),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    latest_revision_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("visualization_revision.id", use_alter=True, name="visualization_latest_revision_id_fk"),
        index=True,
    )
    title: Mapped[Optional[str]] = mapped_column(TEXT)
    type: Mapped[Optional[str]] = mapped_column(TEXT)
    dbkey: Mapped[Optional[str]] = mapped_column(TEXT)
    deleted: Mapped[Optional[bool]] = mapped_column(default=False, index=True)
    importable: Mapped[Optional[bool]] = mapped_column(default=False, index=True)
    slug: Mapped[Optional[str]] = mapped_column(TEXT)
    published: Mapped[Optional[bool]] = mapped_column(default=False, index=True)

    user: Mapped["User"] = relationship()
    revisions: Mapped[List["VisualizationRevision"]] = relationship(
        back_populates="visualization",
        cascade="all, delete-orphan",
        primaryjoin=(lambda: Visualization.id == VisualizationRevision.visualization_id),
    )
    latest_revision: Mapped[Optional["VisualizationRevision"]] = relationship(
        post_update=True,
        primaryjoin=(lambda: Visualization.latest_revision_id == VisualizationRevision.id),
        lazy=False,
    )
    tags: Mapped[List["VisualizationTagAssociation"]] = relationship(
        order_by=lambda: VisualizationTagAssociation.id, back_populates="visualization"
    )
    annotations: Mapped[List["VisualizationAnnotationAssociation"]] = relationship(
        order_by=lambda: VisualizationAnnotationAssociation.id,
        back_populates="visualization",
    )
    ratings: Mapped[List["VisualizationRatingAssociation"]] = relationship(
        order_by=lambda: VisualizationRatingAssociation.id,
        back_populates="visualization",
    )
    users_shared_with: Mapped[List["VisualizationUserShareAssociation"]] = relationship(back_populates="visualization")

    average_rating = None

    # Set up proxy so that
    #   Visualization.users_shared_with
    # returns a list of users that visualization is shared with.
    users_shared_with_dot_users = association_proxy("users_shared_with", "user")

    dict_element_visible_keys = [
        "id",
        "annotation",
        "create_time",
        "db_key",
        "deleted",
        "importable",
        "published",
        "tags",
        "title",
        "type",
        "update_time",
        "username",
    ]

    def __init__(self, **kwd):
        super().__init__(**kwd)
        if self.latest_revision:
            self.revisions.append(self.latest_revision)

    @property
    def annotation(self):
        if len(self.annotations) == 1:
            return self.annotations[0].annotation
        return None

    def copy(self, user=None, title=None):
        """
        Provide copy of visualization with only its latest revision.
        """
        # NOTE: a shallow copy is done: the config is copied as is but datasets
        # are not copied nor are the dataset ids changed. This means that the
        # user does not have a copy of the data in his/her history and the
        # user who owns the datasets may delete them, making them inaccessible
        # for the current user.
        # TODO: a deep copy option is needed.

        if not user:
            user = self.user
        if not title:
            title = self.title

        copy_viz = Visualization(user=user, type=self.type, title=title, dbkey=self.dbkey)
        copy_revision = self.latest_revision.copy(visualization=copy_viz)
        copy_viz.latest_revision = copy_revision
        return copy_viz

    def to_dict(self, view="element"):
        rval = super().to_dict(view=view)
        return rval

    # username needed for slug generation
    @property
    def username(self):
        return self.user.username


class VisualizationRevision(Base, RepresentById):
    __tablename__ = "visualization_revision"
    __table_args__ = (Index("ix_visualization_revision_dbkey", "dbkey", mysql_length=200),)

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)
    visualization_id: Mapped[int] = mapped_column(ForeignKey("visualization.id"), index=True)
    title: Mapped[Optional[str]] = mapped_column(TEXT)
    dbkey: Mapped[Optional[str]] = mapped_column(TEXT)
    config: Mapped[Optional[bytes]] = mapped_column(MutableJSONType)
    visualization: Mapped["Visualization"] = relationship(
        back_populates="revisions",
        primaryjoin=(lambda: Visualization.id == VisualizationRevision.visualization_id),
    )

    def copy(self, visualization=None):
        """
        Returns a copy of this object.
        """
        if not visualization:
            visualization = self.visualization

        return VisualizationRevision(
            visualization=visualization, title=self.title, dbkey=self.dbkey, config=self.config
        )


class VisualizationUserShareAssociation(Base, UserShareAssociation):
    __tablename__ = "visualization_user_share_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    visualization_id: Mapped[int] = mapped_column(ForeignKey("visualization.id"), index=True, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id"), index=True, nullable=True)
    user: Mapped[User] = relationship()
    visualization: Mapped["Visualization"] = relationship(back_populates="users_shared_with")


class Tag(Base, RepresentById):
    __tablename__ = "tag"
    __table_args__ = (UniqueConstraint("name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[Optional[int]]
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tag.id"))
    name: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    children: Mapped[List["Tag"]] = relationship(back_populates="parent")
    parent: Mapped[Optional["Tag"]] = relationship(back_populates="children", remote_side=[id])

    def __str__(self):
        return f"Tag(id={self.id}, type={self.type or -1}, parent_id={self.parent_id}, name={self.name})"


class ItemTagAssociation(Dictifiable):
    dict_collection_visible_keys = ["id", "user_tname", "user_value"]
    dict_element_visible_keys = dict_collection_visible_keys
    user_tname: Mapped[Optional[str]]
    user_value: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def copy(self, cls=None):
        if cls:
            new_ta = cls()
        else:
            new_ta = type(self)()
        new_ta.tag_id = self.tag_id
        new_ta.user_tname = self.user_tname
        new_ta.value = self.value
        new_ta.user_value = self.user_value
        return new_ta


class HistoryTagAssociation(Base, ItemTagAssociation, RepresentById):
    __tablename__ = "history_tag_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    history_id: Mapped[int] = mapped_column(ForeignKey("history.id"), index=True, nullable=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    user_tname: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    history: Mapped["History"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()
    user: Mapped[Optional["User"]] = relationship()


class HistoryDatasetAssociationTagAssociation(Base, ItemTagAssociation, RepresentById):
    __tablename__ = "history_dataset_association_tag_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    history_dataset_association_id: Mapped[int] = mapped_column(
        ForeignKey("history_dataset_association.id"), index=True, nullable=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    user_tname: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    history_dataset_association: Mapped["HistoryDatasetAssociation"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()
    user: Mapped[Optional["User"]] = relationship()


class LibraryDatasetDatasetAssociationTagAssociation(Base, ItemTagAssociation, RepresentById):
    __tablename__ = "library_dataset_dataset_association_tag_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    library_dataset_dataset_association_id: Mapped[int] = mapped_column(
        ForeignKey("library_dataset_dataset_association.id"), index=True, nullable=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    user_tname: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    library_dataset_dataset_association: Mapped["LibraryDatasetDatasetAssociation"] = relationship(
        back_populates="tags"
    )
    tag: Mapped["Tag"] = relationship()
    user: Mapped[Optional["User"]] = relationship()


class PageTagAssociation(Base, ItemTagAssociation, RepresentById):
    __tablename__ = "page_tag_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("page.id"), index=True, nullable=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    user_tname: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    page: Mapped["Page"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()
    user: Mapped[Optional["User"]] = relationship()


class WorkflowStepTagAssociation(Base, ItemTagAssociation, RepresentById):
    __tablename__ = "workflow_step_tag_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_step_id: Mapped[int] = mapped_column(ForeignKey("workflow_step.id"), index=True, nullable=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    user_tname: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    workflow_step: Mapped["WorkflowStep"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()
    user: Mapped[Optional["User"]] = relationship()


class StoredWorkflowTagAssociation(Base, ItemTagAssociation, RepresentById):
    __tablename__ = "stored_workflow_tag_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    stored_workflow_id: Mapped[int] = mapped_column(ForeignKey("stored_workflow.id"), index=True, nullable=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    user_tname: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    stored_workflow: Mapped["StoredWorkflow"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()
    user: Mapped[Optional["User"]] = relationship()


class VisualizationTagAssociation(Base, ItemTagAssociation, RepresentById):
    __tablename__ = "visualization_tag_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    visualization_id: Mapped[int] = mapped_column(ForeignKey("visualization.id"), index=True, nullable=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    user_tname: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    visualization: Mapped["Visualization"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()
    user: Mapped[Optional["User"]] = relationship()


class HistoryDatasetCollectionTagAssociation(Base, ItemTagAssociation, RepresentById):
    __tablename__ = "history_dataset_collection_tag_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    history_dataset_collection_id: Mapped[int] = mapped_column(
        ForeignKey("history_dataset_collection_association.id"), index=True, nullable=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    user_tname: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    dataset_collection: Mapped["HistoryDatasetCollectionAssociation"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()
    user: Mapped[Optional["User"]] = relationship()


class LibraryDatasetCollectionTagAssociation(Base, ItemTagAssociation, RepresentById):
    __tablename__ = "library_dataset_collection_tag_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    library_dataset_collection_id: Mapped[int] = mapped_column(
        ForeignKey("library_dataset_collection_association.id"), index=True, nullable=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    user_tname: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    dataset_collection: Mapped["LibraryDatasetCollectionAssociation"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()
    user: Mapped[Optional["User"]] = relationship()


class ToolTagAssociation(Base, ItemTagAssociation, RepresentById):
    __tablename__ = "tool_tag_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    tool_id: Mapped[str] = mapped_column(TrimmedString(255), index=True, nullable=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    user_tname: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    tag: Mapped["Tag"] = relationship()
    user: Mapped[Optional["User"]] = relationship()


# Item annotation classes.
class HistoryAnnotationAssociation(Base, RepresentById):
    __tablename__ = "history_annotation_association"
    __table_args__ = (Index("ix_history_anno_assoc_annotation", "annotation", mysql_length=200),)

    id: Mapped[int] = mapped_column(primary_key=True)
    history_id: Mapped[int] = mapped_column(ForeignKey("history.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    annotation: Mapped[str] = mapped_column(TEXT, nullable=True)
    history: Mapped["History"] = relationship(back_populates="annotations")
    user: Mapped["User"] = relationship()


class HistoryDatasetAssociationAnnotationAssociation(Base, RepresentById):
    __tablename__ = "history_dataset_association_annotation_association"
    __table_args__ = (Index("ix_history_dataset_anno_assoc_annotation", "annotation", mysql_length=200),)

    id: Mapped[int] = mapped_column(primary_key=True)
    history_dataset_association_id: Mapped[int] = mapped_column(
        ForeignKey("history_dataset_association.id"), index=True, nullable=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    annotation: Mapped[str] = mapped_column(TEXT, nullable=True)
    hda: Mapped["HistoryDatasetAssociation"] = relationship(back_populates="annotations")
    user: Mapped[Optional["User"]] = relationship()


class StoredWorkflowAnnotationAssociation(Base, RepresentById):
    __tablename__ = "stored_workflow_annotation_association"
    __table_args__ = (Index("ix_stored_workflow_ann_assoc_annotation", "annotation", mysql_length=200),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stored_workflow_id: Mapped[int] = mapped_column(ForeignKey("stored_workflow.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    annotation: Mapped[str] = mapped_column(TEXT, nullable=True)
    stored_workflow: Mapped["StoredWorkflow"] = relationship(back_populates="annotations")
    user: Mapped[Optional["User"]] = relationship()


class WorkflowStepAnnotationAssociation(Base, RepresentById):
    __tablename__ = "workflow_step_annotation_association"
    __table_args__ = (Index("ix_workflow_step_ann_assoc_annotation", "annotation", mysql_length=200),)

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_step_id: Mapped[int] = mapped_column(ForeignKey("workflow_step.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    annotation: Mapped[str] = mapped_column(TEXT, nullable=True)
    workflow_step: Mapped["WorkflowStep"] = relationship(back_populates="annotations")
    user: Mapped[Optional["User"]] = relationship()


class PageAnnotationAssociation(Base, RepresentById):
    __tablename__ = "page_annotation_association"
    __table_args__ = (Index("ix_page_annotation_association_annotation", "annotation", mysql_length=200),)

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("page.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    annotation: Mapped[str] = mapped_column(TEXT, nullable=True)
    page: Mapped["Page"] = relationship(back_populates="annotations")
    user: Mapped[Optional["User"]] = relationship()


class VisualizationAnnotationAssociation(Base, RepresentById):
    __tablename__ = "visualization_annotation_association"
    __table_args__ = (Index("ix_visualization_annotation_association_annotation", "annotation", mysql_length=200),)

    id: Mapped[int] = mapped_column(primary_key=True)
    visualization_id: Mapped[int] = mapped_column(ForeignKey("visualization.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    annotation: Mapped[str] = mapped_column(TEXT, nullable=True)
    visualization: Mapped["Visualization"] = relationship(back_populates="annotations")
    user: Mapped[Optional["User"]] = relationship()


class HistoryDatasetCollectionAssociationAnnotationAssociation(Base, RepresentById):
    __tablename__ = "history_dataset_collection_annotation_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    history_dataset_collection_id: Mapped[int] = mapped_column(
        ForeignKey("history_dataset_collection_association.id"), index=True, nullable=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    annotation: Mapped[str] = mapped_column(TEXT, nullable=True)
    history_dataset_collection: Mapped["HistoryDatasetCollectionAssociation"] = relationship(
        back_populates="annotations"
    )
    user: Mapped[Optional["User"]] = relationship()


class LibraryDatasetCollectionAnnotationAssociation(Base, RepresentById):
    __tablename__ = "library_dataset_collection_annotation_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    library_dataset_collection_id: Mapped[int] = mapped_column(
        ForeignKey("library_dataset_collection_association.id"), index=True, nullable=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    annotation: Mapped[str] = mapped_column(TEXT, nullable=True)
    dataset_collection: Mapped["LibraryDatasetCollectionAssociation"] = relationship(back_populates="annotations")
    user: Mapped[Optional["User"]] = relationship()


class Vault(Base):
    __tablename__ = "vault"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    parent_key: Mapped[Optional[str]] = mapped_column(Text, ForeignKey(key), index=True)
    children: Mapped[List["Vault"]] = relationship(back_populates="parent")
    parent: Mapped[Optional["Vault"]] = relationship(back_populates="children", remote_side=[key])
    value: Mapped[Optional[str]] = mapped_column(Text)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=True)


# Item rating classes.
class ItemRatingAssociation(Base):
    __abstract__ = True

    def __init__(self, user, item, rating=0):
        self.user = user
        self.rating = rating
        self._set_item(item)

    def _set_item(self, item):
        """Set association's item."""
        raise NotImplementedError()


class HistoryRatingAssociation(ItemRatingAssociation, RepresentById):
    __tablename__ = "history_rating_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    history_id: Mapped[int] = mapped_column(ForeignKey("history.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    rating: Mapped[int] = mapped_column(index=True, nullable=True)
    history: Mapped["History"] = relationship(back_populates="ratings")
    user: Mapped[Optional["User"]] = relationship()

    def _set_item(self, history):
        add_object_to_object_session(self, history)
        self.history = history


class HistoryDatasetAssociationRatingAssociation(ItemRatingAssociation, RepresentById):
    __tablename__ = "history_dataset_association_rating_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    history_dataset_association_id: Mapped[int] = mapped_column(
        ForeignKey("history_dataset_association.id"), index=True, nullable=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    rating: Mapped[int] = mapped_column(index=True, nullable=True)
    history_dataset_association: Mapped["HistoryDatasetAssociation"] = relationship(back_populates="ratings")
    user: Mapped[Optional["User"]] = relationship()

    def _set_item(self, history_dataset_association):
        add_object_to_object_session(self, history_dataset_association)
        self.history_dataset_association = history_dataset_association


class StoredWorkflowRatingAssociation(ItemRatingAssociation, RepresentById):
    __tablename__ = "stored_workflow_rating_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    stored_workflow_id: Mapped[int] = mapped_column(ForeignKey("stored_workflow.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    rating: Mapped[int] = mapped_column(index=True, nullable=True)
    stored_workflow: Mapped["StoredWorkflow"] = relationship(back_populates="ratings")
    user: Mapped[Optional["User"]] = relationship()

    def _set_item(self, stored_workflow):
        add_object_to_object_session(self, stored_workflow)
        self.stored_workflow = stored_workflow


class PageRatingAssociation(ItemRatingAssociation, RepresentById):
    __tablename__ = "page_rating_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("page.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    rating: Mapped[int] = mapped_column(index=True, nullable=True)
    page: Mapped["Page"] = relationship(back_populates="ratings")
    user: Mapped[Optional["User"]] = relationship()

    def _set_item(self, page):
        add_object_to_object_session(self, page)
        self.page = page


class VisualizationRatingAssociation(ItemRatingAssociation, RepresentById):
    __tablename__ = "visualization_rating_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    visualization_id: Mapped[int] = mapped_column(ForeignKey("visualization.id"), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    rating: Mapped[int] = mapped_column(index=True, nullable=True)
    visualization: Mapped["Visualization"] = relationship(back_populates="ratings")
    user: Mapped[Optional["User"]] = relationship()

    def _set_item(self, visualization):
        add_object_to_object_session(self, visualization)
        self.visualization = visualization


class HistoryDatasetCollectionRatingAssociation(ItemRatingAssociation, RepresentById):
    __tablename__ = "history_dataset_collection_rating_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    history_dataset_collection_id: Mapped[int] = mapped_column(
        ForeignKey("history_dataset_collection_association.id"), index=True, nullable=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    rating: Mapped[int] = mapped_column(index=True, nullable=True)
    dataset_collection: Mapped["HistoryDatasetCollectionAssociation"] = relationship(back_populates="ratings")
    user: Mapped[Optional["User"]] = relationship()

    def _set_item(self, dataset_collection):
        add_object_to_object_session(self, dataset_collection)
        self.dataset_collection = dataset_collection


class LibraryDatasetCollectionRatingAssociation(ItemRatingAssociation, RepresentById):
    __tablename__ = "library_dataset_collection_rating_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    library_dataset_collection_id: Mapped[int] = mapped_column(
        ForeignKey("library_dataset_collection_association.id"), index=True, nullable=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    rating: Mapped[int] = mapped_column(index=True, nullable=True)
    dataset_collection: Mapped["LibraryDatasetCollectionAssociation"] = relationship(back_populates="ratings")
    user: Mapped[Optional["User"]] = relationship()

    def _set_item(self, dataset_collection):
        add_object_to_object_session(self, dataset_collection)
        self.dataset_collection = dataset_collection


# Data manager classes.
class DataManagerHistoryAssociation(Base, RepresentById):
    __tablename__ = "data_manager_history_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(index=True, default=now, onupdate=now, nullable=True)
    history_id: Mapped[Optional[int]] = mapped_column(ForeignKey("history.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    history: Mapped[Optional["History"]] = relationship()
    user: Mapped[Optional["User"]] = relationship(back_populates="data_manager_histories")


class DataManagerJobAssociation(Base, RepresentById):
    __tablename__ = "data_manager_job_association"
    __table_args__ = (Index("ix_data_manager_job_association_data_manager_id", "data_manager_id", mysql_length=200),)

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[datetime] = mapped_column(index=True, default=now, onupdate=now, nullable=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job.id"), index=True)
    data_manager_id: Mapped[Optional[str]] = mapped_column(TEXT)
    job: Mapped[Optional["Job"]] = relationship(back_populates="data_manager_association", uselist=False)


class UserPreference(Base, RepresentById):
    __tablename__ = "user_preference"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    name: Mapped[Optional[str]] = mapped_column(Unicode(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(Text)

    def __init__(self, name=None, value=None):
        # Do not remove this constructor: it is set as the creator for the User.preferences
        # AssociationProxy to which 2 args are passed.
        self.name = name
        self.value = value


class UsesTemplatesAppConfig(Protocol):
    # TODO: delete this config protocol def and uses in dev
    pass


class HasConfigSecrets(RepresentById):
    secret_config_type: str
    template_secrets: Mapped[Optional[CONFIGURATION_TEMPLATE_CONFIGURATION_SECRET_NAMES_TYPE]]
    uuid: Mapped[Union[UUID, str]]
    user: Mapped["User"]

    @classmethod
    def vault_key_from_uuid(clazz, uuid: Union[str, UUID], secret: str, app_config: UsesTemplatesAppConfig) -> str:
        return f"{clazz.secret_config_type}/{str(get_uuid(uuid))}/{secret}"

    def vault_id_prefix(self, app_config: UsesTemplatesAppConfig) -> str:
        id_str = str(self.uuid)
        user_vault_id_prefix = f"{self.secret_config_type}/{id_str}"
        return user_vault_id_prefix

    def vault_key(self, secret: str, app_config: UsesTemplatesAppConfig) -> str:
        user_vault_id_prefix = self.vault_id_prefix(app_config)
        key = f"{user_vault_id_prefix}/{secret}"
        return key


class HasConfigEnvironment(RepresentById):
    template_definition: Mapped[Optional[CONFIGURATION_TEMPLATE_DEFINITION_TYPE]]

    @property
    def template_environment(self) -> TemplateEnvironment:
        definition = self.template_definition
        if not definition:
            return TemplateEnvironment.model_validate([])
        environment = definition.get("environment")
        if not environment:
            return TemplateEnvironment.model_validate([])
        else:
            return TemplateEnvironment.model_validate(environment)


T = TypeVar("T", bound=ConfigTemplate, covariant=True)


class HasConfigTemplate(HasConfigSecrets, HasConfigEnvironment, RepresentById, Generic[T]):
    name: Mapped[str]
    description: Mapped[Optional[str]]
    template_id: Mapped[str]
    template_version: Mapped[int]
    template_variables: Mapped[Optional[CONFIGURATION_TEMPLATE_CONFIGURATION_VARIABLES_TYPE]]
    hidden: Mapped[bool]
    active: Mapped[bool]
    purged: Mapped[bool]

    @property
    def template(self) -> T:
        raise NotImplementedError()


class UserObjectStore(Base, HasConfigTemplate):
    __tablename__ = "user_object_store"
    secret_config_type = "object_store_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("galaxy_user.id"), index=True)
    uuid: Mapped[Union[UUID, str]] = mapped_column(UUIDType(), index=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, index=True)
    # user specified name of the instance they've created
    name: Mapped[str] = mapped_column(String(255), index=True)
    # user specified description of the instance they've created
    description: Mapped[Optional[str]] = mapped_column(Text)
    # active but doesn't appear in user selection
    hidden: Mapped[bool] = mapped_column(default=False)
    # set to False to deactive the source
    active: Mapped[bool] = mapped_column(default=True)
    # a purged file source cannot be re-activated because secrets have been purged
    purged: Mapped[bool] = mapped_column(default=False)
    # the template store id
    template_id: Mapped[str] = mapped_column(String(255), index=True)
    # the template store version (0, 1, ...)
    template_version: Mapped[int] = mapped_column(Integer, index=True)
    # Full template from object_store_templates.yml catalog.
    # For tools we just store references, so here we could easily just use
    # the id/version and not record the definition... as the templates change
    # over time this choice has some big consequences despite being easy to swap
    # implementations.
    template_definition: Mapped[Optional[CONFIGURATION_TEMPLATE_DEFINITION_TYPE]] = mapped_column(JSONType)
    # Big JSON blob of the variable name -> value mapping defined for the store's
    # variables by the user.
    template_variables: Mapped[Optional[CONFIGURATION_TEMPLATE_CONFIGURATION_VARIABLES_TYPE]] = mapped_column(JSONType)
    # Track a list of secrets that were defined for this object store at creation
    template_secrets: Mapped[Optional[CONFIGURATION_TEMPLATE_CONFIGURATION_SECRET_NAMES_TYPE]] = mapped_column(JSONType)

    user: Mapped["User"] = relationship("User", back_populates="object_stores")

    @property
    def template(self) -> ObjectStoreTemplate:
        return ObjectStoreTemplate(**self.template_definition or {})

    def object_store_configuration(
        self, secrets: SecretsDict, environment: EnvironmentDict, templates: Optional[List[ObjectStoreTemplate]] = None
    ) -> ObjectStoreConfiguration:
        if templates is None:
            templates = [self.template]
        user_details = self.user.config_template_details()
        variables: CONFIGURATION_TEMPLATE_CONFIGURATION_VARIABLES_TYPE = self.template_variables or {}
        first_exception = None
        for template in templates:
            try:
                return object_store_template_to_configuration(
                    template,
                    variables=variables,
                    secrets=secrets,
                    user_details=user_details,
                    environment=environment,
                )
            except Exception as e:
                if first_exception is None:
                    first_exception = e
                continue
        if first_exception:
            raise first_exception

        raise ValueError("No template sent to object_store_configuration")


class UserFileSource(Base, HasConfigTemplate):
    __tablename__ = "user_file_source"
    secret_config_type = "file_source_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    uuid: Mapped[Union[UUID, str]] = mapped_column(UUIDType(), index=True)
    create_time: Mapped[datetime] = mapped_column(default=now)
    update_time: Mapped[datetime] = mapped_column(default=now, onupdate=now, index=True)
    # user specified name of the instance they've created
    name: Mapped[str] = mapped_column(String(255), index=True)
    # user specified description of the instance they've created
    description: Mapped[Optional[str]] = mapped_column(Text)
    # active but doesn't appear in user selection
    hidden: Mapped[bool] = mapped_column(default=False)
    # set to False to deactive the source
    active: Mapped[bool] = mapped_column(default=True)
    # a purged file source cannot be re-activated because secrets have been purged
    purged: Mapped[bool] = mapped_column(default=False)
    # the template store id
    template_id: Mapped[str] = mapped_column(String(255), index=True)
    # the template store version (0, 1, ...)
    template_version: Mapped[int] = mapped_column(index=True)
    # Full template from file_sources_templates.yml catalog.
    # For tools we just store references, so here we could easily just use
    # the id/version and not record the definition... as the templates change
    # over time this choice has some big consequences despite being easy to swap
    # implementations.
    template_definition: Mapped[Optional[CONFIGURATION_TEMPLATE_DEFINITION_TYPE]] = mapped_column(JSONType)
    # Big JSON blob of the variable name -> value mapping defined for the store's
    # variables by the user.
    template_variables: Mapped[Optional[CONFIGURATION_TEMPLATE_CONFIGURATION_VARIABLES_TYPE]] = mapped_column(JSONType)
    # Track a list of secrets that were defined for this object store at creation
    template_secrets: Mapped[Optional[CONFIGURATION_TEMPLATE_CONFIGURATION_SECRET_NAMES_TYPE]] = mapped_column(JSONType)

    user: Mapped["User"] = relationship("User", back_populates="file_sources")

    @property
    def template(self) -> FileSourceTemplate:
        return FileSourceTemplate(**self.template_definition or {})

    def file_source_configuration(
        self,
        secrets: SecretsDict,
        environment: EnvironmentDict,
        implicit: ImplicitConfigurationParameters,
        templates: Optional[List[FileSourceTemplate]] = None,
    ) -> FileSourceConfiguration:
        if templates is None:
            templates = [self.template]
        user_details = self.user.config_template_details()
        variables: CONFIGURATION_TEMPLATE_CONFIGURATION_VARIABLES_TYPE = self.template_variables or {}
        first_exception = None
        for template in templates:
            try:
                return file_source_template_to_configuration(
                    template,
                    variables=variables,
                    secrets=secrets,
                    user_details=user_details,
                    environment=environment,
                    implicit=implicit,
                )
            except Exception as e:
                if first_exception is None:
                    first_exception = e
                continue
        if first_exception:
            raise first_exception

        raise ValueError("No template sent to file_source_configuration")


# TODO: add link from tool_request to this
class ToolLandingRequest(Base):
    __tablename__ = "tool_landing_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[Optional[datetime]] = mapped_column(index=True, default=now, onupdate=now, nullable=True)
    uuid: Mapped[Union[UUID, str]] = mapped_column(UUIDType(), index=True)
    tool_id: Mapped[str] = mapped_column(String(255))
    tool_version: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    request_state: Mapped[Optional[Dict]] = mapped_column(JSONType)
    client_secret: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    public: Mapped[bool] = mapped_column(Boolean)

    user: Mapped[Optional["User"]] = relationship()


# TODO: add link from workflow_invocation to this
class WorkflowLandingRequest(Base):
    __tablename__ = "workflow_landing_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    workflow_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stored_workflow.id"), nullable=True)
    stored_workflow_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow.id"), nullable=True)

    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    update_time: Mapped[Optional[datetime]] = mapped_column(index=True, default=now, onupdate=now, nullable=True)
    uuid: Mapped[Union[UUID, str]] = mapped_column(UUIDType(), index=True)
    request_state: Mapped[Optional[Dict]] = mapped_column(JSONType)
    client_secret: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    workflow_source: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    workflow_source_type: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    public: Mapped[bool] = mapped_column(Boolean)

    user: Mapped[Optional["User"]] = relationship()
    stored_workflow: Mapped[Optional["StoredWorkflow"]] = relationship()
    workflow: Mapped[Optional["Workflow"]] = relationship()


class UserAction(Base, RepresentById):
    __tablename__ = "user_action"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_session.id"), index=True)
    action: Mapped[Optional[str]] = mapped_column(Unicode(255))
    context: Mapped[Optional[str]] = mapped_column(Unicode(512))
    params: Mapped[Optional[str]] = mapped_column(Unicode(1024))
    user: Mapped[Optional["User"]] = relationship()


class APIKeys(Base, RepresentById):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    key: Mapped[Optional[str]] = mapped_column(TrimmedString(32), index=True, unique=True)
    user: Mapped[Optional["User"]] = relationship(back_populates="api_keys")
    deleted: Mapped[bool] = mapped_column(index=True, server_default=false())


def copy_list(lst, *args, **kwds):
    if lst is None:
        return lst
    else:
        return [el.copy(*args, **kwds) for el in lst]


def _prepare_metadata_for_serialization(id_encoder, serialization_options, metadata):
    """Prepare metatdata for exporting."""
    processed_metadata = {}
    for name, value in metadata.items():
        # Metadata files are not needed for export because they can be
        # regenerated.
        if isinstance(value, MetadataFile):
            if serialization_options.strip_metadata_files:
                continue
            else:
                value = value.serialize(id_encoder, serialization_options)
        processed_metadata[name] = value

    return processed_metadata


# The following CleanupEvent* models could be defined as tables only;
# however making them models keeps things simple and consistent.


class CleanupEvent(Base):
    __tablename__ = "cleanup_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(TrimmedString(1024))


class CleanupEventDatasetAssociation(Base):
    __tablename__ = "cleanup_event_dataset_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    cleanup_event_id: Mapped[int] = mapped_column(ForeignKey("cleanup_event.id"), index=True, nullable=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dataset.id"), index=True, nullable=True)


class CleanupEventMetadataFileAssociation(Base):
    __tablename__ = "cleanup_event_metadata_file_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    cleanup_event_id: Mapped[int] = mapped_column(ForeignKey("cleanup_event.id"), index=True, nullable=True)
    metadata_file_id: Mapped[int] = mapped_column(ForeignKey("metadata_file.id"), index=True, nullable=True)


class CleanupEventHistoryAssociation(Base):
    __tablename__ = "cleanup_event_history_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    cleanup_event_id: Mapped[int] = mapped_column(ForeignKey("cleanup_event.id"), index=True, nullable=True)
    history_id: Mapped[int] = mapped_column(ForeignKey("history.id"), index=True, nullable=True)


class CleanupEventHistoryDatasetAssociationAssociation(Base):
    __tablename__ = "cleanup_event_hda_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    cleanup_event_id: Mapped[int] = mapped_column(ForeignKey("cleanup_event.id"), index=True, nullable=True)
    hda_id: Mapped[int] = mapped_column(ForeignKey("history_dataset_association.id"), index=True, nullable=True)


class CleanupEventLibraryAssociation(Base):
    __tablename__ = "cleanup_event_library_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    cleanup_event_id: Mapped[int] = mapped_column(ForeignKey("cleanup_event.id"), index=True, nullable=True)
    library_id: Mapped[int] = mapped_column(ForeignKey("library.id"), index=True, nullable=True)


class CleanupEventLibraryFolderAssociation(Base):
    __tablename__ = "cleanup_event_library_folder_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    cleanup_event_id: Mapped[int] = mapped_column(ForeignKey("cleanup_event.id"), index=True, nullable=True)
    library_folder_id: Mapped[int] = mapped_column(ForeignKey("library_folder.id"), index=True, nullable=True)


class CleanupEventLibraryDatasetAssociation(Base):
    __tablename__ = "cleanup_event_library_dataset_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    cleanup_event_id: Mapped[int] = mapped_column(ForeignKey("cleanup_event.id"), index=True, nullable=True)
    library_dataset_id: Mapped[int] = mapped_column(ForeignKey("library_dataset.id"), index=True, nullable=True)


class CleanupEventLibraryDatasetDatasetAssociationAssociation(Base):
    __tablename__ = "cleanup_event_ldda_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    cleanup_event_id: Mapped[int] = mapped_column(ForeignKey("cleanup_event.id"), index=True, nullable=True)
    ldda_id: Mapped[int] = mapped_column(
        ForeignKey("library_dataset_dataset_association.id"), index=True, nullable=True
    )


class CleanupEventImplicitlyConvertedDatasetAssociationAssociation(Base):
    __tablename__ = "cleanup_event_icda_association"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_time: Mapped[datetime] = mapped_column(default=now, nullable=True)
    cleanup_event_id: Mapped[int] = mapped_column(ForeignKey("cleanup_event.id"), index=True, nullable=True)
    icda_id: Mapped[int] = mapped_column(
        ForeignKey("implicitly_converted_dataset_association.id"), index=True, nullable=True
    )


class CeleryUserRateLimit(Base):
    """
    For each user stores the last time a task was scheduled for execution.
    Used to limit the number of tasks allowed per user per second.
    """

    __tablename__ = "celery_user_rate_limit"

    user_id: Mapped[int] = mapped_column(ForeignKey("galaxy_user.id", ondelete="CASCADE"), primary_key=True)
    last_scheduled_time: Mapped[datetime]

    def __repr__(self):
        return (
            f"CeleryUserRateLimit(id_type={self.id_type!r}, "
            f"id={self.id!r}, last_scheduled_time={self.last_scheduled_time!r})"
        )


# The following models (HDA, LDDA) are mapped imperatively (for details see discussion in PR #12064)
# TLDR: there are issues ('metadata' property, Galaxy object wrapping) that need to be addressed separately
# before these models can be mapped declaratively. Keeping them in the mapping module breaks the auth package
# tests (which import model directly bypassing the mapping module); fixing that is possible by importing
# mapping into the test; however, having all models mapped in the same module is cleaner.

HistoryDatasetAssociation.table = Table(
    "history_dataset_association",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True),
    Column("history_id", Integer, ForeignKey("history.id"), index=True),
    Column("dataset_id", Integer, ForeignKey("dataset.id"), index=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now, index=True),
    Column("state", TrimmedString(64), index=True, key="_state"),
    Column(
        "copied_from_history_dataset_association_id",
        Integer,
        ForeignKey("history_dataset_association.id"),
        nullable=True,
    ),
    Column(
        "copied_from_library_dataset_dataset_association_id",
        Integer,
        ForeignKey("library_dataset_dataset_association.id"),
        nullable=True,
    ),
    Column("name", TrimmedString(255)),
    Column("info", TrimmedString(255)),
    Column("blurb", TrimmedString(255)),
    Column("peek", TEXT, key="_peek"),
    Column("tool_version", TEXT),
    Column("extension", TrimmedString(64), index=True),
    Column("metadata", MetadataType, key="_metadata"),
    Column("metadata_deferred", Boolean, key="metadata_deferred"),
    Column("parent_id", Integer, ForeignKey("history_dataset_association.id"), nullable=True),
    Column("designation", TrimmedString(255)),
    Column("deleted", Boolean, index=True, default=False),
    Column("visible", Boolean),
    Column("extended_metadata_id", Integer, ForeignKey("extended_metadata.id"), index=True),
    Column("version", Integer, default=1, nullable=True, index=True),
    Column("hid", Integer),
    Column("purged", Boolean, index=True, default=False),
    Column("validated_state", TrimmedString(64), default="unvalidated", nullable=False),
    Column("validated_state_message", TEXT),
    Column(
        "hidden_beneath_collection_instance_id", ForeignKey("history_dataset_collection_association.id"), nullable=True
    ),
)

LibraryDatasetDatasetAssociation.table = Table(
    "library_dataset_dataset_association",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True),
    Column("library_dataset_id", Integer, ForeignKey("library_dataset.id"), index=True),
    Column("dataset_id", Integer, ForeignKey("dataset.id"), index=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now, index=True),
    Column("state", TrimmedString(64), index=True, key="_state"),
    Column(
        "copied_from_history_dataset_association_id",
        Integer,
        ForeignKey(
            "history_dataset_association.id", use_alter=True, name="history_dataset_association_dataset_id_fkey"
        ),
        nullable=True,
    ),
    Column(
        "copied_from_library_dataset_dataset_association_id",
        Integer,
        ForeignKey(
            "library_dataset_dataset_association.id", use_alter=True, name="library_dataset_dataset_association_id_fkey"
        ),
        nullable=True,
    ),
    Column("name", TrimmedString(255), index=True),
    Column("info", TrimmedString(255)),
    Column("blurb", TrimmedString(255)),
    Column("peek", TEXT, key="_peek"),
    Column("tool_version", TEXT),
    Column("extension", TrimmedString(64)),
    Column("metadata", MetadataType, key="_metadata"),
    Column("metadata_deferred", Boolean, key="metadata_deferred"),
    Column("parent_id", Integer, ForeignKey("library_dataset_dataset_association.id"), nullable=True),
    Column("designation", TrimmedString(255)),
    Column("deleted", Boolean, index=True, default=False),
    Column("validated_state", TrimmedString(64), default="unvalidated", nullable=False),
    Column("validated_state_message", TEXT),
    Column("visible", Boolean),
    Column("extended_metadata_id", Integer, ForeignKey("extended_metadata.id"), index=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("message", TrimmedString(255)),
)


mapper_registry.map_imperatively(
    HistoryDatasetAssociation,
    HistoryDatasetAssociation.table,
    properties=dict(
        dataset=relationship(
            Dataset,
            primaryjoin=(lambda: Dataset.id == HistoryDatasetAssociation.table.c.dataset_id),
            lazy="joined",
            back_populates="history_associations",
        ),
        copied_from_history_dataset_association=relationship(
            HistoryDatasetAssociation,
            primaryjoin=(
                HistoryDatasetAssociation.table.c.copied_from_history_dataset_association_id
                == HistoryDatasetAssociation.table.c.id
            ),
            remote_side=[HistoryDatasetAssociation.table.c.id],
            uselist=False,
            back_populates="copied_to_history_dataset_associations",
        ),
        copied_from_library_dataset_dataset_association=relationship(
            LibraryDatasetDatasetAssociation,
            primaryjoin=(
                LibraryDatasetDatasetAssociation.table.c.id
                == HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id
            ),
            back_populates="copied_to_history_dataset_associations",
        ),
        copied_to_history_dataset_associations=relationship(
            HistoryDatasetAssociation,
            primaryjoin=(
                HistoryDatasetAssociation.table.c.copied_from_history_dataset_association_id
                == HistoryDatasetAssociation.table.c.id
            ),
            back_populates="copied_from_history_dataset_association",
        ),
        copied_to_library_dataset_dataset_associations=relationship(
            LibraryDatasetDatasetAssociation,
            primaryjoin=(
                HistoryDatasetAssociation.table.c.id
                == LibraryDatasetDatasetAssociation.table.c.copied_from_history_dataset_association_id
            ),
            back_populates="copied_from_history_dataset_association",
        ),
        tags=relationship(
            HistoryDatasetAssociationTagAssociation,
            order_by=HistoryDatasetAssociationTagAssociation.id,
            back_populates="history_dataset_association",
        ),
        annotations=relationship(
            HistoryDatasetAssociationAnnotationAssociation,
            order_by=HistoryDatasetAssociationAnnotationAssociation.id,
            back_populates="hda",
        ),
        ratings=relationship(
            HistoryDatasetAssociationRatingAssociation,
            order_by=HistoryDatasetAssociationRatingAssociation.id,
            back_populates="history_dataset_association",
        ),
        extended_metadata=relationship(
            ExtendedMetadata,
            primaryjoin=(HistoryDatasetAssociation.table.c.extended_metadata_id == ExtendedMetadata.id),
        ),
        hidden_beneath_collection_instance=relationship(
            HistoryDatasetCollectionAssociation,
            primaryjoin=(
                HistoryDatasetAssociation.table.c.hidden_beneath_collection_instance_id
                == HistoryDatasetCollectionAssociation.id
            ),
            uselist=False,
        ),
        _metadata=deferred(HistoryDatasetAssociation.table.c._metadata),
        dependent_jobs=relationship(JobToInputDatasetAssociation, back_populates="dataset"),
        creating_job_associations=relationship(JobToOutputDatasetAssociation, back_populates="dataset"),
        history=relationship(History, back_populates="datasets"),
        implicitly_converted_datasets=relationship(
            ImplicitlyConvertedDatasetAssociation,
            primaryjoin=(lambda: ImplicitlyConvertedDatasetAssociation.hda_parent_id == HistoryDatasetAssociation.id),
            back_populates="parent_hda",
        ),
        implicitly_converted_parent_datasets=relationship(
            ImplicitlyConvertedDatasetAssociation,
            primaryjoin=(lambda: ImplicitlyConvertedDatasetAssociation.hda_id == HistoryDatasetAssociation.id),
            back_populates="dataset",
        ),
    ),
)

mapper_registry.map_imperatively(
    LibraryDatasetDatasetAssociation,
    LibraryDatasetDatasetAssociation.table,
    properties=dict(
        dataset=relationship(
            Dataset,
            primaryjoin=(lambda: LibraryDatasetDatasetAssociation.table.c.dataset_id == Dataset.id),
            back_populates="library_associations",
        ),
        library_dataset=relationship(
            LibraryDataset, foreign_keys=LibraryDatasetDatasetAssociation.table.c.library_dataset_id
        ),
        user=relationship(User),
        copied_from_library_dataset_dataset_association=relationship(
            LibraryDatasetDatasetAssociation,
            primaryjoin=(
                LibraryDatasetDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id
                == LibraryDatasetDatasetAssociation.table.c.id
            ),
            remote_side=[LibraryDatasetDatasetAssociation.table.c.id],
            uselist=False,
            back_populates="copied_to_library_dataset_dataset_associations",
        ),
        copied_to_library_dataset_dataset_associations=relationship(
            LibraryDatasetDatasetAssociation,
            primaryjoin=(
                LibraryDatasetDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id
                == LibraryDatasetDatasetAssociation.table.c.id
            ),
            back_populates="copied_from_library_dataset_dataset_association",
        ),
        copied_to_history_dataset_associations=relationship(
            HistoryDatasetAssociation,
            primaryjoin=(
                LibraryDatasetDatasetAssociation.table.c.id
                == HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id
            ),
            back_populates="copied_from_library_dataset_dataset_association",
        ),
        implicitly_converted_datasets=relationship(
            ImplicitlyConvertedDatasetAssociation,
            primaryjoin=(
                ImplicitlyConvertedDatasetAssociation.ldda_parent_id == LibraryDatasetDatasetAssociation.table.c.id
            ),
            back_populates="parent_ldda",
        ),
        tags=relationship(
            LibraryDatasetDatasetAssociationTagAssociation,
            order_by=LibraryDatasetDatasetAssociationTagAssociation.id,
            back_populates="library_dataset_dataset_association",
        ),
        extended_metadata=relationship(
            ExtendedMetadata,
            primaryjoin=(LibraryDatasetDatasetAssociation.table.c.extended_metadata_id == ExtendedMetadata.id),
        ),
        _metadata=deferred(LibraryDatasetDatasetAssociation.table.c._metadata),
        actions=relationship(
            LibraryDatasetDatasetAssociationPermissions, back_populates="library_dataset_dataset_association"
        ),
        dependent_jobs=relationship(JobToInputLibraryDatasetAssociation, back_populates="dataset"),
        creating_job_associations=relationship(JobToOutputLibraryDatasetAssociation, back_populates="dataset"),
        implicitly_converted_parent_datasets=relationship(
            ImplicitlyConvertedDatasetAssociation,
            primaryjoin=(lambda: ImplicitlyConvertedDatasetAssociation.ldda_id == LibraryDatasetDatasetAssociation.id),
            back_populates="dataset_ldda",
        ),
        copied_from_history_dataset_association=relationship(
            HistoryDatasetAssociation,
            primaryjoin=(
                HistoryDatasetAssociation.table.c.id
                == LibraryDatasetDatasetAssociation.table.c.copied_from_history_dataset_association_id
            ),
            back_populates="copied_to_library_dataset_dataset_associations",
        ),
    ),
)

# ----------------------------------------------------------------------------------------
# The following statements must not precede the mapped models defined above.

Job.any_output_dataset_collection_instances_deleted = deferred(
    column_property(  # type:ignore[assignment]
        exists(HistoryDatasetCollectionAssociation.id).where(
            and_(
                Job.id == JobToOutputDatasetCollectionAssociation.job_id,
                HistoryDatasetCollectionAssociation.id == JobToOutputDatasetCollectionAssociation.dataset_collection_id,
                HistoryDatasetCollectionAssociation.deleted == true(),
            )
        ),
    )
)

Job.any_output_dataset_deleted = deferred(
    column_property(  # type:ignore[assignment]
        exists(HistoryDatasetAssociation.id).where(
            and_(
                Job.id == JobToOutputDatasetAssociation.job_id,
                HistoryDatasetAssociation.table.c.id == JobToOutputDatasetAssociation.dataset_id,
                HistoryDatasetAssociation.table.c.deleted == true(),
            )
        ),
    )
)

History.average_rating = column_property(  # type:ignore[assignment]
    select(func.avg(HistoryRatingAssociation.rating))
    .where(HistoryRatingAssociation.history_id == History.id)
    .scalar_subquery(),
    deferred=True,
)

History.users_shared_with_count = column_property(  # type:ignore[assignment]
    select(func.count(HistoryUserShareAssociation.id))
    .where(History.id == HistoryUserShareAssociation.history_id)
    .scalar_subquery(),
    deferred=True,
)

Page.average_rating = column_property(
    select(func.avg(PageRatingAssociation.rating)).where(PageRatingAssociation.page_id == Page.id).scalar_subquery(),
    deferred=True,
)

StoredWorkflow.average_rating = column_property(  # type:ignore[assignment]
    select(func.avg(StoredWorkflowRatingAssociation.rating))
    .where(StoredWorkflowRatingAssociation.stored_workflow_id == StoredWorkflow.id)
    .scalar_subquery(),
    deferred=True,
)

Visualization.average_rating = column_property(  # type:ignore[assignment]
    select(func.avg(VisualizationRatingAssociation.rating))
    .where(VisualizationRatingAssociation.visualization_id == Visualization.id)
    .scalar_subquery(),
    deferred=True,
)

Workflow.step_count = column_property(  # type:ignore[assignment]
    select(func.count(WorkflowStep.id)).where(Workflow.id == WorkflowStep.workflow_id).scalar_subquery(), deferred=True
)

WorkflowInvocationStep.subworkflow_invocation_id = column_property(
    select(WorkflowInvocationToSubworkflowInvocationAssociation.subworkflow_invocation_id)
    .where(
        and_(
            WorkflowInvocationToSubworkflowInvocationAssociation.workflow_invocation_id
            == WorkflowInvocationStep.workflow_invocation_id,
            WorkflowInvocationToSubworkflowInvocationAssociation.workflow_step_id
            == WorkflowInvocationStep.workflow_step_id,
        )
    )
    .scalar_subquery(),
)

# Set up proxy so that this syntax is possible:
# <user_obj>.preferences[pref_name] = pref_value
User.preferences = association_proxy("_preferences", "value", creator=UserPreference)

# Optimized version of getting the current Galaxy session.
# See https://github.com/sqlalchemy/sqlalchemy/discussions/7638 for approach
session_partition = select(
    GalaxySession,
    func.row_number()
    .over(order_by=GalaxySession.update_time.desc(), partition_by=GalaxySession.user_id)
    .label("index"),
).alias()
partitioned_session = aliased(GalaxySession, session_partition)
User.current_galaxy_session = relationship(
    partitioned_session,
    primaryjoin=and_(partitioned_session.user_id == User.id, session_partition.c.index < 2),
    uselist=False,
    viewonly=True,
)


@event.listens_for(HistoryDatasetCollectionAssociation, "init")
def receive_init(target, args, kwargs):
    """
    Listens for the 'init' event. This is not called when 'target' is loaded from the database.
    https://docs.sqlalchemy.org/en/14/orm/events.html#sqlalchemy.orm.InstanceEvents.init

    Addresses SQLAlchemy 2.0 compatibility issue: see inline documentation for
    `add_object_to_object_session` in galaxy.model.orm.util.
    """
    for key in ("history", "copied_from_history_dataset_collection_association"):
        obj = kwargs.get(key)
        if obj:
            add_object_to_object_session(target, obj)
            return  # Once is enough.


JobStateSummary = NamedTuple("JobStateSummary", [(value, int) for value in enum_values(Job.states)] + [("all_jobs", int)])  # type: ignore[misc]  # Ref https://github.com/python/mypy/issues/848#issuecomment-255237167

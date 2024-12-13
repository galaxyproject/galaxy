import logging
from typing import (
    Any,
    Dict,
    Optional,
    TYPE_CHECKING,
    Union,
)
from uuid import UUID

from sqlalchemy import (
    select,
    sql,
    true,
    update,
)

from galaxy import (
    exceptions,
    model,
)
from galaxy.exceptions import DuplicatedIdentifierException
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import (
    DynamicTool,
    UserDynamicToolAssociation,
)
from galaxy.schema.tools import (
    DynamicToolPayload,
    DynamicUnprivilegedToolCreatePayload,
)
from galaxy.tool_util.cwl import tool_proxy
from .base import (
    ModelManager,
    raise_filter_err,
)
from .executables import artifact_class

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from galaxy.managers.base import OrmFilterParsersType
    from galaxy.managers.context import ProvidesUserContext


class DynamicToolManager(ModelManager[model.DynamicTool]):
    """Manages dynamic tools stored in Galaxy's database."""

    model_class = model.DynamicTool

    def get_tool_by_id_or_uuid(self, id_or_uuid: Union[int, str]):
        if isinstance(id_or_uuid, int):
            return self.get_tool_by_id(id_or_uuid)
        else:
            return self.get_tool_by_uuid(id_or_uuid)

    def get_tool_by_uuid(self, uuid: Optional[Union[UUID, str]]):
        stmt = select(DynamicTool).where(DynamicTool.uuid == uuid)
        return self.session().scalars(stmt).one_or_none()

    def get_tool_by_tool_id(self, tool_id):
        stmt = select(DynamicTool).where(DynamicTool.tool_id == tool_id, DynamicTool.public == true())
        return self.session().scalars(stmt).one_or_none()

    def get_unprivileged_tool_by_uuid(self, user: model.User, uuid: Union[UUID, str]):
        stmt = self.owned_unprivileged_statement(user).where(DynamicTool.uuid == uuid)
        return self.session().scalars(stmt).one_or_none()

    def get_unprivileged_tool_by_tool_id(self, user: model.User, tool_id: str):
        stmt = self.owned_unprivileged_statement(user).where(DynamicTool.tool_id == tool_id)
        return self.session().scalars(stmt).one_or_none()

    def get_tool_by_id(self, object_id):
        stmt = select(DynamicTool).where(DynamicTool.id == object_id, DynamicTool.public == true())
        return self.session().scalars(stmt).one_or_none()

    def create_tool(self, trans: ProvidesUserContext, tool_payload: DynamicToolPayload, allow_load=True):
        if not getattr(self.app.config, "enable_beta_tool_formats", False):
            raise exceptions.ConfigDoesNotAllowException(
                "Set 'enable_beta_tool_formats' in Galaxy config to create dynamic tools."
            )

        dynamic_tool = None
        uuid_str = tool_payload.uuid
        # Convert uuid_str to UUID or generate new if None
        uuid = model.get_uuid(uuid_str)
        if uuid_str:
            # TODO: enforce via DB constraint and catch appropriate
            # exception.
            dynamic_tool = self.get_tool_by_uuid(uuid_str)
            if dynamic_tool:
                if not allow_load:
                    raise DuplicatedIdentifierException(
                        f"Attempted to create dynamic tool with duplicate UUID '{uuid_str}'"
                    )
                assert dynamic_tool.uuid == uuid
        if not dynamic_tool:
            if tool_payload.src == "from_path":
                tool_format, representation, _ = artifact_class(None, tool_payload.model_dump())
            else:
                representation = tool_payload.representation.model_dump(by_alias=True, exclude_unset=True)
                if not representation:
                    raise exceptions.ObjectAttributeMissingException("A tool 'representation' is required.")

                tool_format = representation.get("class")
                if not tool_format:
                    raise exceptions.ObjectAttributeMissingException("Current tool representations require 'class'.")

            tool_directory: Optional[str] = None
            tool_path: Optional[str] = None
            if tool_payload.src == "from_path":
                tool_directory = tool_payload.tool_directory
                tool_path = tool_payload.path

            if tool_format in ("GalaxyTool", "GalaxyUserTool"):
                tool_id = representation.get("id")
                if not tool_id:
                    tool_id = str(uuid)
            elif tool_format in ("CommandLineTool", "ExpressionTool"):
                # CWL tools
                if tool_path:
                    proxy = tool_proxy(tool_path=tool_path, uuid=uuid)
                else:
                    # Build a tool proxy so that we can convert to the persistable
                    # hash.
                    proxy = tool_proxy(
                        tool_object=representation["raw_process_reference"],
                        tool_directory=tool_directory,
                        uuid=uuid,
                    )
                tool_id = proxy.galaxy_id()
            else:
                raise Exception(f"Unknown tool format [{tool_format}] encountered.")
            tool_version = representation.get("version")
            dynamic_tool = self.create(
                tool_format=tool_format,
                tool_id=tool_id,
                tool_version=tool_version,
                tool_path=tool_path,
                tool_directory=tool_directory,
                uuid=uuid,
                active=tool_payload.active,
                hidden=tool_payload.hidden,
                value=representation,
                public=True,
            )
        self.app.toolbox.load_dynamic_tool(dynamic_tool)
        return dynamic_tool

    def create_unprivileged_tool(
        self, user: model.User, tool_payload: DynamicUnprivilegedToolCreatePayload
    ) -> DynamicTool:
        if not getattr(self.app.config, "enable_beta_tool_formats", False):
            raise exceptions.ConfigDoesNotAllowException(
                "Set 'enable_beta_tool_formats' in Galaxy config to create dynamic tools."
            )

        dynamic_tool = self.create(
            tool_format=tool_payload.representation.class_,
            tool_id=tool_payload.representation.id,
            tool_version=tool_payload.representation.version,
            active=tool_payload.active,
            hidden=tool_payload.hidden,
            value=tool_payload.representation.model_dump(by_alias=True),
            public=False,
            flush=True,
        )
        session = self.session()
        session.add(UserDynamicToolAssociation(user_id=user.id, dynamic_tool_id=dynamic_tool.id))
        session.commit()
        return dynamic_tool

    def list_tools(self, active=True):
        stmt = select(DynamicTool).where(DynamicTool.active == active)
        return self.session().scalars(stmt)

    def list_unprivileged_tools(self, user: model.User, active=True):
        owned_statement = self.owned_unprivileged_statement(user=user)
        stmt = owned_statement.where(
            DynamicTool.active == active,
            UserDynamicToolAssociation.active == active,
        )
        return self.session().scalars(stmt)

    def owned_unprivileged_statement(self, user: model.User):
        return (
            select(DynamicTool)
            .join(UserDynamicToolAssociation, DynamicTool.id == UserDynamicToolAssociation.dynamic_tool_id)
            .where(
                UserDynamicToolAssociation.user_id == user.id,
            )
            .order_by(UserDynamicToolAssociation.id.desc())
        )

    def deactivate_unprivileged_tool(self, user: model.User, dynamic_tool: DynamicTool):
        update_stmt = (
            update(UserDynamicToolAssociation)
            .where(
                UserDynamicToolAssociation.user_id == user.id,
                UserDynamicToolAssociation.dynamic_tool_id == dynamic_tool.id,
            )
            .values(active=False)
        )
        self.session().execute(update_stmt)

    def deactivate(self, dynamic_tool):
        self.update(dynamic_tool, {"active": False})
        return dynamic_tool


class ToolFilterMixin:
    orm_filter_parsers: "OrmFilterParsersType"

    def create_tool_filter(self, attr, op, val):
        def _create_tool_filter(model_class=None):
            if op == "eq":
                cond = model.Job.table.c.tool_id == val
            elif op == "contains":
                cond = model.Job.table.c.tool_id.contains(val, autoescape=True)
            else:
                raise_filter_err(attr, op, val, "bad op in filter")
            if model_class is model.HistoryDatasetAssociation:
                return sql.expression.and_(
                    model.Job.table.c.id == model.JobToOutputDatasetAssociation.table.c.job_id,
                    model.HistoryDatasetAssociation.table.c.id
                    == model.JobToOutputDatasetAssociation.table.c.dataset_id,
                    cond,
                )
            elif model_class is model.HistoryDatasetCollectionAssociation:
                return sql.expression.and_(
                    model.Job.id == model.JobToOutputDatasetAssociation.job_id,
                    model.JobToOutputDatasetAssociation.dataset_id == model.DatasetCollectionElement.hda_id,
                    model.DatasetCollectionElement.dataset_collection_id
                    == model.HistoryDatasetCollectionAssociation.collection_id,
                    cond,
                )
            else:
                return True

        return _create_tool_filter

    def _add_parsers(self):
        self.orm_filter_parsers.update(
            {
                "tool_id": self.create_tool_filter,
            }
        )

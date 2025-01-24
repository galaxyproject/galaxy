import logging
from typing import (
    Optional,
    TYPE_CHECKING,
    Union,
)
from uuid import UUID

from sqlalchemy import (
    select,
    sql,
)

from galaxy import (
    exceptions,
    model,
)
from galaxy.exceptions import DuplicatedIdentifierException
from galaxy.model import DynamicTool
from galaxy.tool_util.cwl import tool_proxy
from .base import (
    ModelManager,
    raise_filter_err,
)
from .executables import artifact_class

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from galaxy.managers.base import OrmFilterParsersType


class DynamicToolManager(ModelManager[model.DynamicTool]):
    """Manages dynamic tools stored in Galaxy's database."""

    model_class = model.DynamicTool

    def get_tool_by_uuid(self, uuid: Optional[Union[UUID, str]]):
        stmt = select(DynamicTool).where(DynamicTool.uuid == uuid)
        return self.session().scalars(stmt).one_or_none()

    def get_tool_by_tool_id(self, tool_id):
        stmt = select(DynamicTool).where(DynamicTool.tool_id == tool_id)
        return self.session().scalars(stmt).one_or_none()

    def get_tool_by_id(self, object_id):
        stmt = select(DynamicTool).where(DynamicTool.id == object_id)
        return self.session().scalars(stmt).one_or_none()

    def create_tool(self, trans, tool_payload, allow_load=True):
        if not getattr(self.app.config, "enable_beta_tool_formats", False):
            raise exceptions.ConfigDoesNotAllowException(
                "Set 'enable_beta_tool_formats' in Galaxy config to create dynamic tools."
            )

        dynamic_tool = None
        uuid_str = tool_payload.get("uuid")
        # Convert uuid_str to UUID or generate new if None
        uuid = model.get_uuid(uuid_str)
        if uuid_str:
            # TODO: enforce via DB constraint and catch appropriate
            # exception.
            dynamic_tool = self.get_tool_by_uuid(uuid_str)
            if dynamic_tool:
                if not allow_load:
                    raise DuplicatedIdentifierException(dynamic_tool.id)
                assert dynamic_tool.uuid == uuid
        if not dynamic_tool:
            src = tool_payload.get("src", "representation")
            is_path = src == "from_path"

            if is_path:
                tool_format, representation, _ = artifact_class(None, tool_payload)
            else:
                assert src == "representation"
                representation = tool_payload.get("representation")
                if not representation:
                    raise exceptions.ObjectAttributeMissingException("A tool 'representation' is required.")

                tool_format = representation.get("class")
                if not tool_format:
                    raise exceptions.ObjectAttributeMissingException("Current tool representations require 'class'.")

            tool_path = tool_payload.get("path")
            tool_directory = tool_payload.get("tool_directory")
            if tool_format == "GalaxyTool":
                tool_id = representation.get("id")
                if not tool_id:
                    tool_id = str(uuid)
            elif tool_format in ("CommandLineTool", "ExpressionTool"):
                # CWL tools
                if is_path:
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
                active=tool_payload.get("active"),
                hidden=tool_payload.get("hidden"),
                value=representation,
            )
        self.app.toolbox.load_dynamic_tool(dynamic_tool)
        return dynamic_tool

    def list_tools(self, active=True):
        stmt = select(DynamicTool).where(DynamicTool.active == active)
        return self.session().scalars(stmt)

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

from typing import (
    List,
    Optional,
)

from pydantic import BaseModel
from sqlalchemy import (
    cast,
    Integer,
    select,
)

from galaxy.model.scoped_session import install_model_scoped_session
from galaxy.model.tool_shed_install import ToolShedRepository
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    Security,
)
from galaxy.schema.schema import (
    CheckForUpdatesResponse,
    InstalledToolShedRepository,
)
from galaxy.tool_shed.util.repository_util import check_for_updates
from galaxy.util.tool_shed.tool_shed_registry import Registry
from galaxy.web import url_for


class InstalledToolShedRepositoryIndexRequest(BaseModel):
    name: Optional[str] = None
    owner: Optional[str] = None
    changeset: Optional[str] = None
    deleted: Optional[bool] = None
    uninstalled: Optional[bool] = None


class ToolShedRepositoriesService:
    def __init__(
        self,
        install_model_context: install_model_scoped_session,
        tool_shed_registry: Registry,
    ):
        self._install_model_context = install_model_context
        self._tool_shed_registry = tool_shed_registry

    def index(self, request: InstalledToolShedRepositoryIndexRequest) -> List[InstalledToolShedRepository]:
        repositories = self._get_tool_shed_repositories(
            name=request.name,
            owner=request.owner,
            changeset_revision=request.changeset,
            deleted=request.deleted,
            uninstalled=request.uninstalled,
        )
        index = []
        for repository in repositories:
            index.append(self._show(repository))
        return index

    def show(self, repository_id: DecodedDatabaseIdField) -> InstalledToolShedRepository:
        tool_shed_repository = self._install_model_context.get(ToolShedRepository, repository_id)
        assert tool_shed_repository
        return self._show(tool_shed_repository)

    def check_for_updates(self, repository_id: Optional[int]) -> CheckForUpdatesResponse:
        message, status = check_for_updates(self._tool_shed_registry, self._install_model_context, repository_id)
        return CheckForUpdatesResponse(message=message, status=status)

    def _show(self, tool_shed_repository: ToolShedRepository) -> InstalledToolShedRepository:
        tool_shed_repository_dict = tool_shed_repository.as_dict()
        encoded_id = Security.security.encode_id(tool_shed_repository.id)
        tool_shed_repository_dict["error_message"] = tool_shed_repository.error_message or ""
        tool_shed_repository_dict["url"] = url_for("tool_shed_repositories", id=encoded_id)
        return InstalledToolShedRepository(**tool_shed_repository_dict)

    def _get_tool_shed_repositories(self, **kwd):
        stmt = select(ToolShedRepository)
        for key, value in kwd.items():
            if value is not None:
                column = ToolShedRepository.__table__.c[key]  # type:ignore[attr-defined]
                stmt = stmt.filter(column == value)
        stmt = stmt.order_by(ToolShedRepository.name).order_by(cast(ToolShedRepository.ctx_rev, Integer).desc())
        session = self._install_model_context
        return session.scalars(stmt).all()

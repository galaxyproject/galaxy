from typing import (
    List,
    Optional,
)

from pydantic import BaseModel
from sqlalchemy import (
    and_,
    cast,
    Integer,
)

from galaxy.model.scoped_session import install_model_scoped_session
from galaxy.model.tool_shed_install import ToolShedRepository
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    CheckForUpdatesResponse,
    InstalledToolShedRepository,
)
from galaxy.tool_shed.util.repository_util import (
    check_for_updates,
    get_tool_shed_repository_by_decoded_id,
)
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
        clause_list = []
        if request.name is not None:
            clause_list.append(ToolShedRepository.table.c.name == request.name)
        if request.owner is not None:
            clause_list.append(ToolShedRepository.table.c.owner == request.owner)
        if request.changeset is not None:
            clause_list.append(ToolShedRepository.table.c.changeset_revision == request.changeset)
        if request.deleted is not None:
            clause_list.append(ToolShedRepository.table.c.deleted == request.deleted)
        if request.uninstalled is not None:
            clause_list.append(ToolShedRepository.table.c.uninstalled == request.uninstalled)
        query = (
            self._install_model_context.query(ToolShedRepository)
            .order_by(ToolShedRepository.table.c.name)
            .order_by(cast(ToolShedRepository.ctx_rev, Integer).desc())
        )
        if len(clause_list) > 0:
            query = query.filter(and_(*clause_list))
        index = []
        for repository in query.all():
            index.append(self._show(repository))
        return index

    def show(self, repository_id: DecodedDatabaseIdField) -> InstalledToolShedRepository:
        tool_shed_repository = get_tool_shed_repository_by_decoded_id(self._install_model_context, int(repository_id))
        return self._show(tool_shed_repository)

    def check_for_updates(self, repository_id: Optional[int]) -> CheckForUpdatesResponse:
        message, status = check_for_updates(self._tool_shed_registry, self._install_model_context, repository_id)
        return CheckForUpdatesResponse(message=message, status=status)

    def _show(self, tool_shed_repository: ToolShedRepository) -> InstalledToolShedRepository:
        tool_shed_repository_dict = tool_shed_repository.as_dict()
        encoded_id = DecodedDatabaseIdField.encode(tool_shed_repository.id)
        tool_shed_repository_dict["id"] = encoded_id
        tool_shed_repository_dict["error_message"] = tool_shed_repository.error_message or ""
        tool_shed_repository_dict["url"] = url_for("tool_shed_repositories", id=encoded_id)
        return InstalledToolShedRepository(**tool_shed_repository_dict)

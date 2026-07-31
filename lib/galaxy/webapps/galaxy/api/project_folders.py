"""
API operations on project folders, an optional per-user grouping of histories.
"""

import logging

from fastapi import (
    Body,
    Path,
    Response,
    status,
)

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.histories import HistoryManager
from galaxy.managers.project_folders import ProjectFolderManager
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.project_folders import (
    CreateProjectFolderPayload,
    ProjectFolderSummary,
    SetHistoryProjectFolderPayload,
    UpdateProjectFolderPayload,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["project folders"])

FolderIdPathParam = Path(..., title="Project Folder ID", description="The encoded ID of the project folder.")
HistoryIdPathParam = Path(..., title="History ID", description="The encoded ID of the history.")


@router.cbv
class FastAPIProjectFolders:
    manager: ProjectFolderManager = depends(ProjectFolderManager)
    history_manager: HistoryManager = depends(HistoryManager)

    @router.get(
        "/api/project_folders",
        summary="Return the project folders owned by the current user.",
    )
    def index(self, trans: ProvidesHistoryContext = DependsOnTrans) -> list[ProjectFolderSummary]:
        return [self._summary(folder, count) for folder, count in self.manager.index(trans)]

    @router.post(
        "/api/project_folders",
        summary="Create a new project folder.",
        status_code=status.HTTP_201_CREATED,
    )
    def create(
        self,
        payload: CreateProjectFolderPayload = Body(...),
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> ProjectFolderSummary:
        folder = self.manager.create(trans, payload.name)
        return self._summary(folder, 0)

    @router.put(
        "/api/project_folders/{folder_id}",
        summary="Rename a project folder.",
    )
    def update(
        self,
        folder_id: DecodedDatabaseIdField = FolderIdPathParam,
        payload: UpdateProjectFolderPayload = Body(...),
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> ProjectFolderSummary:
        folder = self.manager.update(trans, folder_id, payload.name)
        return self._summary(folder, len([h for h in folder.histories if not h.deleted]))

    @router.delete(
        "/api/project_folders/{folder_id}",
        summary="Delete a project folder, leaving its histories in place.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete(
        self,
        folder_id: DecodedDatabaseIdField = FolderIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ):
        self.manager.delete(trans, folder_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(
        "/api/histories/{history_id}/project_folder",
        summary="File a history under a project folder, or unfile it.",
    )
    def set_history_folder(
        self,
        history_id: DecodedDatabaseIdField = HistoryIdPathParam,
        payload: SetHistoryProjectFolderPayload = Body(...),
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> ProjectFolderSummary | None:
        history = self.history_manager.get_owned(history_id, trans.user, current_history=trans.history)
        self.manager.set_history_folder(trans, history, payload.project_folder_id)
        folder = history.project_folder
        if folder is None:
            return None
        return self._summary(folder, len([h for h in folder.histories if not h.deleted]))

    def _summary(self, folder, count: int) -> ProjectFolderSummary:
        return ProjectFolderSummary(
            id=folder.id,
            name=folder.name,
            create_time=folder.create_time,
            update_time=folder.update_time,
            count=count,
        )

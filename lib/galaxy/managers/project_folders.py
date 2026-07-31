"""Manager for project folders, an optional per-user grouping of histories."""

import logging

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.exc import IntegrityError

from galaxy import (
    exceptions,
    model,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


class ProjectFolderManager:
    """Folders are private to their owner, so every lookup is scoped by user.

    They carry no permissions of their own: filing a history under a folder
    must never change who can reach that history.
    """

    def __init__(self, app: MinimalManagerApp) -> None:
        self.app = app

    @property
    def session(self):
        return self.app.model.session

    def _require_user(self, trans: ProvidesUserContext) -> model.User:
        if not trans.user:
            raise exceptions.AuthenticationRequired("Project folders require a logged in user.")
        return trans.user

    def index(self, trans: ProvidesUserContext) -> list[tuple[model.ProjectFolder, int]]:
        """Return the user's folders with the number of histories in each."""
        user = self._require_user(trans)
        history_count = (
            select(model.History.project_folder_id, func.count(model.History.id).label("count"))
            .where(model.History.deleted == False)  # noqa: E712
            .group_by(model.History.project_folder_id)
            .subquery()
        )
        statement = (
            select(model.ProjectFolder, func.coalesce(history_count.c.count, 0))
            .outerjoin(history_count, history_count.c.project_folder_id == model.ProjectFolder.id)
            .where(model.ProjectFolder.user_id == user.id)
            .order_by(model.ProjectFolder.name)
        )
        return [(folder, count) for folder, count in self.session.execute(statement)]

    def get(self, trans: ProvidesUserContext, folder_id: int) -> model.ProjectFolder:
        user = self._require_user(trans)
        folder = self.session.get(model.ProjectFolder, folder_id)
        # Report someone else's folder as missing rather than forbidden, so the
        # API does not confirm that an id exists to a user who cannot see it.
        if folder is None or folder.user_id != user.id:
            raise exceptions.ObjectNotFound("Project folder not found.")
        return folder

    def create(self, trans: ProvidesUserContext, name: str) -> model.ProjectFolder:
        user = self._require_user(trans)
        folder = model.ProjectFolder(user_id=user.id, name=name.strip())
        self.session.add(folder)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise exceptions.Conflict(f"A project folder named '{name}' already exists.")
        return folder

    def update(self, trans: ProvidesUserContext, folder_id: int, name: str) -> model.ProjectFolder:
        folder = self.get(trans, folder_id)
        folder.name = name.strip()
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise exceptions.Conflict(f"A project folder named '{name}' already exists.")
        return folder

    def delete(self, trans: ProvidesUserContext, folder_id: int) -> None:
        """Delete a folder, releasing its histories rather than deleting them."""
        folder = self.get(trans, folder_id)
        self.session.delete(folder)
        self.session.commit()

    def set_history_folder(
        self, trans: ProvidesUserContext, history: model.History, folder_id: int | None
    ) -> model.History:
        """File a history under a folder, or unfile it when folder_id is None."""
        user = self._require_user(trans)
        if history.user_id != user.id:
            raise exceptions.ItemOwnershipException("Histories can only be filed by their owner.")
        # get() enforces that the folder belongs to this user, so a history
        # cannot be filed into someone else's folder.
        history.project_folder_id = self.get(trans, folder_id).id if folder_id is not None else None
        self.session.commit()
        return history

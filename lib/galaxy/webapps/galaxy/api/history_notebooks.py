"""
API for history notebooks.
"""

from typing import Annotated

from fastapi import (
    Body,
    Path,
    Response,
    status,
)

from galaxy.exceptions import (
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.histories import HistoryManager
from galaxy.managers.history_notebooks import HistoryNotebookManager
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    CreateHistoryNotebookPayload,
    HistoryNotebookDetails,
    HistoryNotebookList,
    HistoryNotebookRevisionDetails,
    HistoryNotebookRevisionList,
    HistoryNotebookRevisionSummary,
    HistoryNotebookSummary,
    PrepareNotebookForPageResponse,
    UpdateHistoryNotebookPayload,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)

router = Router(tags=["history_notebooks"])

HistoryIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="History ID", description="The ID of the History."),
]

NotebookIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Notebook ID", description="The ID of the Notebook."),
]

RevisionIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Revision ID", description="The ID of the Revision."),
]


def _latest_revision_fields(notebook):
    """Extract content fields from notebook's latest revision."""
    rev = notebook.latest_revision
    assert rev is not None, f"Notebook {notebook.id} has no revisions"
    return {
        "content": rev.content,
        "content_format": rev.content_format,
        "edit_source": rev.edit_source,
    }


@router.cbv
class FastAPIHistoryNotebooks:
    manager: HistoryNotebookManager = depends(HistoryNotebookManager)
    history_manager: HistoryManager = depends(HistoryManager)

    @router.get(
        "/api/histories/{history_id}/notebooks",
        summary="List all notebooks for a history.",
        response_description="List of notebook summaries.",
    )
    def index(
        self,
        history_id: HistoryIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> HistoryNotebookList:
        """List all notebooks for this history."""
        history = self.history_manager.get_accessible(history_id, trans.user, current_history=trans.history)
        notebooks = self.manager.list_notebooks(trans, history.id)
        return HistoryNotebookList(
            root=[
                HistoryNotebookSummary(
                    id=nb.id,
                    history_id=nb.history_id,
                    title=nb.title,
                    latest_revision_id=nb.latest_revision_id,
                    revision_ids=[r.id for r in nb.revisions],
                    deleted=nb.deleted or False,
                    create_time=nb.create_time,
                    update_time=nb.update_time,
                )
                for nb in notebooks
            ]
        )

    @router.get(
        "/api/histories/{history_id}/notebooks/{notebook_id}",
        summary="Get a specific notebook.",
        response_description="The notebook details including content.",
    )
    def show(
        self,
        history_id: HistoryIdPathParam,
        notebook_id: NotebookIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> HistoryNotebookDetails:
        """Get notebook by ID."""
        history = self.history_manager.get_accessible(history_id, trans.user, current_history=trans.history)
        notebook = self.manager.get_notebook_by_id(trans, notebook_id)
        # Verify notebook belongs to this history
        if notebook.history_id != history.id:
            raise ObjectNotFound(f"Notebook {notebook_id} not found in history {history_id}")

        rval = notebook.to_dict()
        rval.update(_latest_revision_fields(notebook))
        self.manager.rewrite_content_for_export(trans, history, rval)
        return HistoryNotebookDetails(**rval)

    @router.get(
        "/api/histories/{history_id}/notebooks/{notebook_id}/prepare-for-page",
        summary="Prepare notebook content for Page creation.",
        response_description="Notebook content with encoded IDs, ready for POST /api/pages.",
    )
    def prepare_for_page(
        self,
        history_id: HistoryIdPathParam,
        notebook_id: NotebookIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> PrepareNotebookForPageResponse:
        """Resolve HID references and encode IDs for Page creation."""
        history = self.history_manager.get_accessible(history_id, trans.user, current_history=trans.history)
        notebook = self.manager.get_notebook_by_id(trans, notebook_id)
        if notebook.history_id != history.id:
            raise ObjectNotFound(f"Notebook {notebook_id} not found in history {history_id}")
        content = self.manager.prepare_content_for_page(trans, notebook)
        return PrepareNotebookForPageResponse(
            content=content,
            title=notebook.title or "Untitled Notebook",
        )

    @router.post(
        "/api/histories/{history_id}/notebooks",
        summary="Create a new notebook for a history.",
        response_description="The created notebook.",
    )
    def create(
        self,
        history_id: HistoryIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        payload: CreateHistoryNotebookPayload = Body(...),
    ) -> HistoryNotebookDetails:
        """Create a new notebook for the history (multiple notebooks allowed)."""
        history = self.history_manager.get_owned(history_id, trans.user, current_history=trans.history)
        notebook = self.manager.create_notebook(trans, history, payload)

        rval = notebook.to_dict()
        rval.update(_latest_revision_fields(notebook))
        self.manager.rewrite_content_for_export(trans, history, rval)
        return HistoryNotebookDetails(**rval)

    @router.put(
        "/api/histories/{history_id}/notebooks/{notebook_id}",
        summary="Update notebook content (creates new revision).",
        response_description="The updated notebook.",
    )
    def update(
        self,
        history_id: HistoryIdPathParam,
        notebook_id: NotebookIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        payload: UpdateHistoryNotebookPayload = Body(...),
    ) -> HistoryNotebookDetails:
        """Update notebook content. Creates a new revision."""
        history = self.history_manager.get_owned(history_id, trans.user, current_history=trans.history)
        notebook = self.manager.get_notebook_by_id(trans, notebook_id)
        if notebook.history_id != history.id:
            raise ObjectNotFound(f"Notebook {notebook_id} not found in history {history_id}")

        self.manager.save_new_revision(trans, notebook, payload, edit_source=payload.edit_source or "user")

        rval = notebook.to_dict()
        rval.update(_latest_revision_fields(notebook))
        self.manager.rewrite_content_for_export(trans, history, rval)
        return HistoryNotebookDetails(**rval)

    @router.delete(
        "/api/histories/{history_id}/notebooks/{notebook_id}",
        summary="Soft-delete a notebook.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete(
        self,
        history_id: HistoryIdPathParam,
        notebook_id: NotebookIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ):
        """Soft-delete notebook (sets deleted=True)."""
        history = self.history_manager.get_owned(history_id, trans.user, current_history=trans.history)
        notebook = self.manager.get_notebook_by_id(trans, notebook_id)
        if notebook.history_id != history.id:
            raise ObjectNotFound(f"Notebook {notebook_id} not found in history {history_id}")

        self.manager.delete_notebook(trans, notebook)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(
        "/api/histories/{history_id}/notebooks/{notebook_id}/undelete",
        summary="Restore a soft-deleted notebook.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def undelete(
        self,
        history_id: HistoryIdPathParam,
        notebook_id: NotebookIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ):
        """Restore a soft-deleted notebook."""
        history = self.history_manager.get_owned(history_id, trans.user, current_history=trans.history)
        notebook = self.manager.get_notebook_by_id(trans, notebook_id, include_deleted=True)
        if notebook.history_id != history.id:
            raise ObjectNotFound(f"Notebook {notebook_id} not found in history {history_id}")
        if not notebook.deleted:
            raise RequestParameterInvalidException("Notebook is not deleted")

        self.manager.undelete_notebook(trans, notebook)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(
        "/api/histories/{history_id}/notebooks/{notebook_id}/revisions",
        summary="List all revisions for a notebook.",
        response_description="List of revision summaries.",
    )
    def list_revisions(
        self,
        history_id: HistoryIdPathParam,
        notebook_id: NotebookIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> HistoryNotebookRevisionList:
        """List all revisions for a notebook."""
        history = self.history_manager.get_accessible(history_id, trans.user, current_history=trans.history)
        notebook = self.manager.get_notebook_by_id(trans, notebook_id)
        if notebook.history_id != history.id:
            raise ObjectNotFound(f"Notebook {notebook_id} not found in history {history_id}")

        revisions = self.manager.list_revisions(trans, notebook)
        return HistoryNotebookRevisionList(
            root=[
                HistoryNotebookRevisionSummary(
                    id=r.id,
                    notebook_id=r.notebook_id,
                    edit_source=r.edit_source,
                    create_time=r.create_time,
                    update_time=r.update_time,
                )
                for r in revisions
            ]
        )

    @router.get(
        "/api/histories/{history_id}/notebooks/{notebook_id}/revisions/{revision_id}",
        summary="Get a specific revision with content.",
        response_description="Revision details including content.",
    )
    def show_revision(
        self,
        history_id: HistoryIdPathParam,
        notebook_id: NotebookIdPathParam,
        revision_id: RevisionIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> HistoryNotebookRevisionDetails:
        """Get a specific revision by ID, including content."""
        history = self.history_manager.get_accessible(history_id, trans.user, current_history=trans.history)
        notebook = self.manager.get_notebook_by_id(trans, notebook_id)
        if notebook.history_id != history.id:
            raise ObjectNotFound(f"Notebook {notebook_id} not found in history {history_id}")

        revision = self.manager.get_revision(trans, revision_id)
        if revision.notebook_id != notebook.id:
            raise ObjectNotFound(f"Revision {revision_id} not found in notebook {notebook_id}")

        rval = {
            "id": revision.id,
            "notebook_id": revision.notebook_id,
            "content": revision.content,
            "content_format": revision.content_format,
            "edit_source": revision.edit_source,
            "create_time": revision.create_time,
            "update_time": revision.update_time,
        }
        self.manager.rewrite_content_for_export(trans, history, rval)
        return HistoryNotebookRevisionDetails(**rval)

    @router.post(
        "/api/histories/{history_id}/notebooks/{notebook_id}/revisions/{revision_id}/revert",
        summary="Restore notebook to a previous revision.",
        response_description="The newly created revision (copy of the restored content).",
    )
    def revert_to_revision(
        self,
        history_id: HistoryIdPathParam,
        notebook_id: NotebookIdPathParam,
        revision_id: RevisionIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> HistoryNotebookDetails:
        """Restore notebook to a previous revision. Creates a new revision with the old content."""
        history = self.history_manager.get_owned(history_id, trans.user, current_history=trans.history)
        notebook = self.manager.get_notebook_by_id(trans, notebook_id)
        if notebook.history_id != history.id:
            raise ObjectNotFound(f"Notebook {notebook_id} not found in history {history_id}")

        revision = self.manager.get_revision(trans, revision_id)
        if revision.notebook_id != notebook.id:
            raise ObjectNotFound(f"Revision {revision_id} not found in notebook {notebook_id}")

        self.manager.restore_revision(trans, notebook, revision)

        rval = notebook.to_dict()
        rval.update(_latest_revision_fields(notebook))
        self.manager.rewrite_content_for_export(trans, history, rval)
        return HistoryNotebookDetails(**rval)

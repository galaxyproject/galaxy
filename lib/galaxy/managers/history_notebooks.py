"""Manager for history notebook operations."""

from sqlalchemy import (
    false,
    select,
)

from galaxy import model
from galaxy.exceptions import (
    ObjectNotFound,
    RequestParameterMissingException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.markdown_util import (
    ready_galaxy_markdown_for_export,
    ready_galaxy_markdown_for_import,
)
from galaxy.schema.schema import (
    CreateHistoryNotebookPayload,
    UpdateHistoryNotebookPayload,
)


class HistoryNotebookManager:
    """Manager for history notebook operations.

    History notebooks store markdown using the same directive format as Pages
    (e.g., history_dataset_id=X with unencoded integer IDs in the DB).
    On save, ready_galaxy_markdown_for_import() decodes encoded IDs to integers.
    On load, ready_galaxy_markdown_for_export() encodes integers for the client.
    """

    def list_notebooks(
        self, trans: ProvidesUserContext, history_id: int, include_deleted: bool = False
    ) -> list[model.HistoryNotebook]:
        """List all notebooks for a history."""
        stmt = (
            select(model.HistoryNotebook)
            .filter_by(history_id=history_id)
            .order_by(model.HistoryNotebook.update_time.desc())
        )
        if not include_deleted:
            stmt = stmt.filter(model.HistoryNotebook.deleted == false())
        return list(trans.sa_session.scalars(stmt))

    def get_notebook_by_id(
        self, trans: ProvidesUserContext, notebook_id: int, include_deleted: bool = False
    ) -> model.HistoryNotebook:
        """Get notebook by ID, raises if not found."""
        notebook = trans.sa_session.get(model.HistoryNotebook, notebook_id)
        if not notebook:
            raise ObjectNotFound(f"Notebook {notebook_id} not found")
        if notebook.deleted and not include_deleted:
            raise ObjectNotFound(f"Notebook {notebook_id} not found")
        return notebook

    def create_notebook(
        self,
        trans: ProvidesUserContext,
        history: model.History,
        payload: CreateHistoryNotebookPayload,
    ) -> model.HistoryNotebook:
        """Create a new notebook for a history (multiple notebooks allowed)."""
        # Create notebook with title (title on notebook, not revision)
        notebook = model.HistoryNotebook()
        notebook.history = history
        notebook.title = payload.title or history.name

        content = payload.content or ""
        content_format = getattr(payload.content_format, "value", payload.content_format) or "markdown"

        # Decode encoded IDs to integers for DB storage (mirrors Page pipeline)
        if content and content_format == "markdown":
            content = ready_galaxy_markdown_for_import(trans, content)

        revision = model.HistoryNotebookRevision()
        revision.notebook = notebook
        revision.content = content
        revision.content_format = content_format
        revision.edit_source = "user"

        notebook.latest_revision = revision

        session = trans.sa_session
        session.add(notebook)
        session.commit()

        return notebook

    def save_new_revision(
        self,
        trans: ProvidesUserContext,
        notebook: model.HistoryNotebook,
        payload: UpdateHistoryNotebookPayload,
        edit_source: str = "user",
    ) -> model.HistoryNotebookRevision:
        """Create a new revision for the notebook."""
        content = payload.content
        if not content:
            raise RequestParameterMissingException("content required")

        if payload.content_format:
            content_format = getattr(payload.content_format, "value", payload.content_format)
        else:
            assert notebook.latest_revision is not None
            content_format = notebook.latest_revision.content_format

        # Update title on notebook if provided (title not versioned)
        if payload.title:
            notebook.title = payload.title

        # Decode encoded IDs to integers for DB storage (mirrors Page pipeline)
        if content_format == "markdown":
            content = ready_galaxy_markdown_for_import(trans, content)

        revision = model.HistoryNotebookRevision()
        revision.notebook = notebook
        revision.content = content
        revision.content_format = content_format
        revision.edit_source = edit_source

        notebook.latest_revision = revision

        session = trans.sa_session
        session.commit()

        return revision

    def list_revisions(
        self, trans: ProvidesUserContext, notebook: model.HistoryNotebook
    ) -> list[model.HistoryNotebookRevision]:
        """List all revisions for a notebook."""
        stmt = (
            select(model.HistoryNotebookRevision)
            .filter_by(notebook_id=notebook.id)
            .order_by(model.HistoryNotebookRevision.create_time.desc())
        )
        return list(trans.sa_session.scalars(stmt))

    def get_revision(self, trans: ProvidesUserContext, revision_id: int) -> model.HistoryNotebookRevision:
        """Get a specific revision by ID."""
        revision = trans.sa_session.get(model.HistoryNotebookRevision, revision_id)
        if not revision:
            raise ObjectNotFound(f"Revision {revision_id} not found")
        return revision

    def restore_revision(
        self,
        trans: ProvidesUserContext,
        notebook: model.HistoryNotebook,
        revision: model.HistoryNotebookRevision,
    ) -> model.HistoryNotebookRevision:
        """Restore a notebook to an old revision by creating a new revision with its content."""
        new_revision = model.HistoryNotebookRevision()
        new_revision.notebook = notebook
        new_revision.content = revision.content
        new_revision.content_format = revision.content_format
        new_revision.edit_source = "restore"

        notebook.latest_revision = new_revision

        session = trans.sa_session
        session.commit()

        return new_revision

    def prepare_content_for_page(
        self,
        trans: ProvidesUserContext,
        notebook: model.HistoryNotebook,
    ) -> str:
        """Encode IDs for Page creation.

        Returns markdown with encoded IDs, matching the format that
        POST /api/pages expects (same as invocation report content).
        """
        assert notebook.latest_revision is not None
        content = notebook.latest_revision.content
        if not content:
            return ""
        export_content, _, _ = ready_galaxy_markdown_for_export(trans, content)
        return export_content

    def rewrite_content_for_export(self, trans: ProvidesUserContext, history: model.History, rval: dict) -> None:
        """Process notebook content for API response.

        Produces two content fields:
        - content: inline embeds expanded to values + IDs encoded (for Markdown renderer)
        - content_editor: inline embeds as directive syntax + IDs encoded (for text editor)
        """
        content = rval.get("content")
        if content:
            content, content_expanded, _ = ready_galaxy_markdown_for_export(trans, content)
            rval["content"] = content_expanded
            rval["content_editor"] = content
        else:
            rval["content_editor"] = content

    def delete_notebook(self, trans: ProvidesUserContext, notebook: model.HistoryNotebook) -> None:
        """Soft-delete a notebook (sets deleted=True)."""
        notebook.deleted = True
        trans.sa_session.commit()

    def undelete_notebook(self, trans: ProvidesUserContext, notebook: model.HistoryNotebook) -> None:
        """Restore a soft-deleted notebook."""
        notebook.deleted = False
        trans.sa_session.commit()

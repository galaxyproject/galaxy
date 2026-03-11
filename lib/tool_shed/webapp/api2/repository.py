"""Legacy Galaxy→ToolShed install protocol endpoints.

These endpoints are called by Galaxy's install infrastructure to resolve
repository dependencies, check for updates, and retrieve installation metadata.
They were previously implemented on the Pylons ``RepositoryController`` and are
migrated here so the legacy WSGI controller can be deleted.
"""

import logging
import mimetypes
import os
from typing import Optional

from fastapi import Form
from galaxy.exceptions import ObjectNotFound
from galaxy.tool_shed.util.repository_util import get_absolute_path_to_file_in_repository
from starlette.responses import (
    FileResponse,
    Response,
)

from tool_shed.context import SessionRequestContext
from tool_shed.managers.repositories import (
    get_changeset_revision_and_ctx_rev_str,
    get_ctx_rev_for_repository,
    get_repository_dependencies_for_install,
    get_repository_type_str,
    get_required_repo_info_dict_from_encoded,
    get_tool_dependencies_for_changeset,
    next_installable_changeset_revision_str,
    previous_changeset_revisions_str,
    updated_changeset_revisions_str,
)
from tool_shed.util.repository_util import get_repository_in_tool_shed
from tool_shed.structured_app import ToolShedApp
from . import (
    depends,
    DependsOnTrans,
    FromTipQueryParam,
    RequiredChangesetParam,
    RequiredRepoNameParam,
    RequiredRepoOwnerParam,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["legacy_install"])


@router.cbv
class FastAPILegacyInstall:
    app: ToolShedApp = depends(ToolShedApp)


    @router.get(
        "/repository/get_ctx_rev",
        operation_id="legacy_install__get_ctx_rev",
    )
    def get_ctx_rev(
        self,
        name: str = RequiredRepoNameParam,
        owner: str = RequiredRepoOwnerParam,
        changeset_revision: str = RequiredChangesetParam,
    ) -> Response:
        result = get_ctx_rev_for_repository(self.app, name, owner, changeset_revision)
        return Response(content=result, media_type="text/plain")

    @router.get(
        "/repository/get_changeset_revision_and_ctx_rev",
        operation_id="legacy_install__get_changeset_revision_and_ctx_rev",
    )
    def get_changeset_revision_and_ctx_rev(
        self,
        name: str = RequiredRepoNameParam,
        owner: str = RequiredRepoOwnerParam,
        changeset_revision: str = RequiredChangesetParam,
    ) -> Response:
        result = get_changeset_revision_and_ctx_rev_str(self.app, name, owner, changeset_revision)
        return Response(content=result, media_type="text/plain")

    @router.get(
        "/repository/next_installable_changeset_revision",
        operation_id="legacy_install__next_installable_changeset_revision",
    )
    def next_installable_changeset_revision(
        self,
        name: str = RequiredRepoNameParam,
        owner: str = RequiredRepoOwnerParam,
        changeset_revision: str = RequiredChangesetParam,
    ) -> Response:
        result = next_installable_changeset_revision_str(self.app, name, owner, changeset_revision)
        return Response(content=result, media_type="text/plain")

    @router.get(
        "/repository/previous_changeset_revisions",
        operation_id="legacy_install__previous_changeset_revisions",
    )
    def previous_changeset_revisions(
        self,
        name: str = RequiredRepoNameParam,
        owner: str = RequiredRepoOwnerParam,
        changeset_revision: str = RequiredChangesetParam,
        from_tip: bool = FromTipQueryParam,
    ) -> Response:
        result = previous_changeset_revisions_str(self.app, name, owner, changeset_revision, from_tip=from_tip)
        return Response(content=result, media_type="text/plain")

    @router.get(
        "/repository/updated_changeset_revisions",
        operation_id="legacy_install__updated_changeset_revisions",
    )
    def updated_changeset_revisions(
        self,
        name: str = RequiredRepoNameParam,
        owner: str = RequiredRepoOwnerParam,
        changeset_revision: str = RequiredChangesetParam,
    ) -> Response:
        result = updated_changeset_revisions_str(self.app, name, owner, changeset_revision)
        return Response(content=result, media_type="text/plain")

    @router.get(
        "/repository/get_repository_type",
        operation_id="legacy_install__get_repository_type",
    )
    def get_repository_type(
        self,
        name: str = RequiredRepoNameParam,
        owner: str = RequiredRepoOwnerParam,
    ) -> Response:
        result = get_repository_type_str(self.app, name, owner)
        return Response(content=result, media_type="text/plain")

    @router.get(
        "/repository/get_tool_dependencies",
        operation_id="legacy_install__get_tool_dependencies",
    )
    def get_tool_dependencies(
        self,
        name: str = RequiredRepoNameParam,
        owner: str = RequiredRepoOwnerParam,
        changeset_revision: str = RequiredChangesetParam,
    ) -> Response:
        result = get_tool_dependencies_for_changeset(self.app, name, owner, changeset_revision)
        return Response(content=result, media_type="text/plain")


    @router.get(
        "/repository/get_repository_dependencies",
        operation_id="legacy_install__get_repository_dependencies",
    )
    def get_repository_dependencies(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        name: str = RequiredRepoNameParam,
        owner: str = RequiredRepoOwnerParam,
        changeset_revision: str = RequiredChangesetParam,
    ) -> str:
        # Galaxy does json.loads(text) → tool_shed_decode(result).
        # Returning the encoded string directly: FastAPI JSON-serializes it to "encoded_value".
        return get_repository_dependencies_for_install(self.app, trans, name, owner, changeset_revision)

    @router.get(
        "/repository/get_required_repo_info_dict",
        operation_id="legacy_install__get_required_repo_info_dict_get",
    )
    def get_required_repo_info_dict_via_get(self) -> dict:
        # Galaxy first does a GET (to follow redirects).  Return empty dict
        # so it doesn't 404; the real work happens on POST.
        return {}

    @router.post(
        "/repository/get_required_repo_info_dict",
        operation_id="legacy_install__get_required_repo_info_dict",
    )
    def get_required_repo_info_dict(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_str: Optional[str] = Form(default=None),
    ) -> dict:
        return get_required_repo_info_dict_from_encoded(trans, encoded_str)


    @router.get(
        "/repository/static/images/{repository_id}/{image_file:path}",
        operation_id="legacy_install__display_image",
        tags=["legacy_install"],
    )
    def display_image_in_repository(
        self,
        repository_id: str,
        image_file: str,
    ) -> FileResponse:
        repository = get_repository_in_tool_shed(self.app, repository_id)
        if not repository:
            raise ObjectNotFound("Repository not found.")
        repo_files_dir = repository.repo_path(self.app)
        path_to_file = get_absolute_path_to_file_in_repository(repo_files_dir, image_file)
        if not path_to_file or not os.path.exists(path_to_file):
            raise ObjectNotFound("Image file not found.")
        # Validate resolved path stays within repository directory (symlink protection)
        resolved = os.path.realpath(path_to_file)
        repo_dir_resolved = os.path.realpath(repo_files_dir)
        if resolved != repo_dir_resolved and not resolved.startswith(repo_dir_resolved + os.sep):
            raise ObjectNotFound("Image file not found.")
        # Determine MIME type - try datatypes registry first, fall back to stdlib
        media_type = None
        file_name = os.path.basename(image_file)
        try:
            extension = file_name.rsplit(".", 1)[-1]
            media_type = self.app.datatypes_registry.get_mimetype_by_extension(extension)
        except Exception:
            pass
        if not media_type or media_type == "application/octet-stream":
            guessed, _ = mimetypes.guess_type(file_name)
            if guessed:
                media_type = guessed
        # Only serve known image types
        if not media_type or not media_type.startswith("image/"):
            raise ObjectNotFound("Image file not found.")
        return FileResponse(path=resolved, media_type=media_type)

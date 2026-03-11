"""Legacy Galaxy→ToolShed install protocol endpoints.

These endpoints are called by Galaxy's install infrastructure to resolve
repository dependencies, check for updates, and retrieve installation metadata.
They were previously implemented on the Pylons ``RepositoryController`` and are
migrated here so the legacy WSGI controller can be deleted.
"""

import logging
from typing import Optional

from fastapi import Form
from starlette.responses import Response

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

    # -- plain-text GET endpoints (Galaxy reads response.text) ---------

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

    # -- JSON endpoints (Galaxy reads json.loads(response.text)) -------

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

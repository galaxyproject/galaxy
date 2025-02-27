import os
import shutil
import tempfile
from typing import (
    cast,
    IO,
    List,
    Optional,
    Union,
)

from fastapi import (
    Body,
    Depends,
    Request,
    Response,
    status,
    UploadFile,
)
from starlette.datastructures import UploadFile as StarletteUploadFile

from galaxy.exceptions import (
    ActionInputError,
    InsufficientPermissionsException,
)
from galaxy.webapps.galaxy.api import as_form
from tool_shed.context import SessionRequestContext
from tool_shed.managers.repositories import (
    can_manage_repo,
    can_update_repo,
    check_updates,
    create_repository,
    ensure_can_manage,
    get_install_info,
    get_ordered_installable_revisions,
    get_repository_metadata_dict,
    get_repository_metadata_for_management,
    IndexRequest,
    index_repositories,
    readmes,
    reset_metadata_on_repository,
    search,
    to_detailed_model,
    to_model,
    UpdatesRequest,
    upload_tar_and_set_metadata,
)
from tool_shed.structured_app import ToolShedApp
from tool_shed.util.repository_util import (
    get_repository_in_tool_shed,
    update_validated_repository,
)
from tool_shed_client.schema import (
    CreateRepositoryRequest,
    DetailedRepository,
    from_legacy_install_info,
    InstallInfo,
    Repository,
    RepositoryMetadata,
    RepositoryPermissions,
    RepositoryRevisionReadmes,
    RepositorySearchResults,
    RepositoryUpdate,
    RepositoryUpdateRequest,
    ResetMetadataOnRepositoryRequest,
    ResetMetadataOnRepositoryResponse,
    UpdateRepositoryRequest,
    ValidRepostiroyUpdateMessage,
)
from . import (
    ChangesetRevisionPathParam,
    CommitMessageQueryParam,
    depend_on_either_json_or_form_data,
    depends,
    DependsOnTrans,
    DownloadableQueryParam,
    OptionalHexlifyParam,
    OptionalRepositoryIdParam,
    OptionalRepositoryNameParam,
    OptionalRepositoryOwnerParam,
    RepositoryIdPathParam,
    RepositoryIndexDeletedQueryParam,
    RepositoryIndexNameQueryParam,
    RepositoryIndexOwnerQueryParam,
    RepositoryIndexQueryParam,
    RepositorySearchPageQueryParam,
    RepositorySearchPageSizeQueryParam,
    RequiredChangesetParam,
    RequiredRepoNameParam,
    RequiredRepoOwnerParam,
    RequiredRepositoryChangesetRevisionParam,
    Router,
    UsernameIdPathParam,
)

router = Router(tags=["repositories"])

IndexResponse = Union[RepositorySearchResults, List[Repository]]


@as_form
class RepositoryUpdateRequestFormData(RepositoryUpdateRequest):
    pass


@router.cbv
class FastAPIRepositories:
    app: ToolShedApp = depends(ToolShedApp)

    @router.get(
        "/api/repositories",
        description="Get a list of repositories or perform a search.",
        operation_id="repositories__index",
    )
    def index(
        self,
        q: Optional[str] = RepositoryIndexQueryParam,
        page: Optional[int] = RepositorySearchPageQueryParam,
        page_size: Optional[int] = RepositorySearchPageSizeQueryParam,
        deleted: Optional[bool] = RepositoryIndexDeletedQueryParam,
        owner: Optional[str] = RepositoryIndexOwnerQueryParam,
        name: Optional[str] = RepositoryIndexNameQueryParam,
        trans: SessionRequestContext = DependsOnTrans,
    ) -> IndexResponse:
        if q:
            assert page is not None
            assert page_size is not None
            search_results = search(trans, q, page, page_size)
            return RepositorySearchResults(**search_results)
        # See API notes - was added in https://github.com/galaxyproject/galaxy/pull/3626/files
        # but I think is currently unused. So probably we should just drop it until someone
        # complains.
        # elif params.tool_ids:
        #    response = index_tool_ids(self.app, params.tool_ids)
        #    return response
        else:
            index_request = IndexRequest(
                owner=owner,
                name=name,
                deleted=deleted or False,
            )
            repositories = index_repositories(self.app, index_request)
            return [to_model(self.app, r) for r in repositories]

    @router.get(
        "/api/repositories/get_repository_revision_install_info",
        description="Get information used by the install client to install this repository.",
        operation_id="repositories__legacy_install_info",
    )
    def legacy_install_info(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        name: str = RequiredRepoNameParam,
        owner: str = RequiredRepoOwnerParam,
        changeset_revision: str = RequiredChangesetParam,
    ) -> list:
        legacy_install_info = get_install_info(
            trans,
            name,
            owner,
            changeset_revision,
        )
        return list(legacy_install_info)

    @router.get(
        "/api/repositories/install_info",
        description="Get information used by the install client to install this repository.",
        operation_id="repositories__install_info",
    )
    def install_info(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        name: str = RequiredRepoNameParam,
        owner: str = RequiredRepoOwnerParam,
        changeset_revision: str = RequiredChangesetParam,
    ) -> InstallInfo:
        # A less problematic version of the above API, but I guess we
        # need to maintain the older version for older Galaxy API clients
        # for... sometime... or forever.
        legacy_install_info = get_install_info(
            trans,
            name,
            owner,
            changeset_revision,
        )
        return from_legacy_install_info(legacy_install_info)

    @router.get(
        "/api/repositories/{encoded_repository_id}/metadata",
        description="Get information about repository metadata",
        operation_id="repositories__metadata",
        # See comment below.
        # response_model=RepositoryMetadata,
    )
    def metadata(
        self,
        encoded_repository_id: str = RepositoryIdPathParam,
        downloadable_only: bool = DownloadableQueryParam,
    ) -> dict:
        recursive = True
        as_dict = get_repository_metadata_dict(self.app, encoded_repository_id, recursive, downloadable_only)
        # fails 1020 if we try to use the model - I guess repository dependencies
        # are getting lost
        return as_dict

    @router.get(
        "/api_internal/repositories/{encoded_repository_id}/metadata",
        description="Get information about repository metadata",
        operation_id="repositories__internal_metadata",
        response_model=RepositoryMetadata,
    )
    def metadata_internal(
        self,
        encoded_repository_id: str = RepositoryIdPathParam,
        downloadable_only: bool = DownloadableQueryParam,
    ) -> RepositoryMetadata:
        recursive = True
        as_dict = get_repository_metadata_dict(self.app, encoded_repository_id, recursive, downloadable_only)
        return RepositoryMetadata(root=as_dict)

    @router.get(
        "/api/repositories/get_ordered_installable_revisions",
        description="Get an ordered list of the repository changeset revisions that are installable",
        operation_id="repositories__get_ordered_installable_revisions",
    )
    def get_ordered_installable_revisions(
        self,
        owner: Optional[str] = OptionalRepositoryOwnerParam,
        name: Optional[str] = OptionalRepositoryNameParam,
        tsr_id: Optional[str] = OptionalRepositoryIdParam,
    ) -> List[str]:
        return get_ordered_installable_revisions(self.app, name, owner, tsr_id)

    @router.post(
        "/api/repositories/reset_metadata_on_repository",
        description="reset metadata on a repository",
        operation_id="repositories__reset_legacy",
    )
    def reset_metadata_on_repository_legacy(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        request: ResetMetadataOnRepositoryRequest = depend_on_either_json_or_form_data(
            ResetMetadataOnRepositoryRequest
        ),
    ) -> ResetMetadataOnRepositoryResponse:
        return reset_metadata_on_repository(trans, request.repository_id)

    @router.post(
        "/api/repositories/{encoded_repository_id}/reset_metadata",
        description="reset metadata on a repository",
        operation_id="repositories__reset",
    )
    def reset_metadata_on_repository(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_repository_id: str = RepositoryIdPathParam,
    ) -> ResetMetadataOnRepositoryResponse:
        return reset_metadata_on_repository(trans, encoded_repository_id)

    @router.get(
        "/api/repositories/updates",
        operation_id="repositories__update",
    )
    @router.get(
        "/api/repositories/updates/",
    )
    def updates(
        self,
        owner: Optional[str] = OptionalRepositoryOwnerParam,
        name: Optional[str] = OptionalRepositoryNameParam,
        changeset_revision: str = RequiredRepositoryChangesetRevisionParam,
        hexlify: Optional[bool] = OptionalHexlifyParam,
    ):
        request = UpdatesRequest(
            name=name,
            owner=owner,
            changeset_revision=changeset_revision,
            hexlify=hexlify,
        )
        return Response(content=check_updates(self.app, request))

    @router.post(
        "/api/repositories",
        description="create a new repository",
        operation_id="repositories__create",
    )
    def create(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        request: CreateRepositoryRequest = Body(...),
    ) -> Repository:
        db_repository = create_repository(
            trans,
            request,
        )
        return to_model(self.app, db_repository)

    @router.get(
        "/api/repositories/{encoded_repository_id}",
        operation_id="repositories__show",
    )
    def show(
        self,
        encoded_repository_id: str = RepositoryIdPathParam,
    ) -> DetailedRepository:
        repository = get_repository_in_tool_shed(self.app, encoded_repository_id)
        return to_detailed_model(self.app, repository)

    @router.put(
        "/api/repositories/{encoded_repository_id}",
        operation_id="repositories__update_repository",
    )
    def update_repository(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_repository_id: str = RepositoryIdPathParam,
        request: UpdateRepositoryRequest = Body(...),
    ) -> DetailedRepository:
        repository = get_repository_in_tool_shed(self.app, encoded_repository_id)
        ensure_can_manage(trans, repository)

        # may want to set some of these to null, so we're using the exclude_unset feature
        # to just serialize the ones we want to use to a dictionary.
        update_dictionary = request.model_dump(exclude_unset=True)
        repo_result, message = update_validated_repository(trans, repository, **update_dictionary)
        if repo_result is None:
            raise ActionInputError(message)

        return to_detailed_model(self.app, repository)

    @router.get(
        "/api/repositories/{encoded_repository_id}/permissions",
        operation_id="repositories__permissions",
    )
    def permissions(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_repository_id: str = RepositoryIdPathParam,
    ) -> RepositoryPermissions:
        repository = get_repository_in_tool_shed(self.app, encoded_repository_id)
        if not can_update_repo(trans, repository):
            raise InsufficientPermissionsException(
                "You do not have permission to inspect repository repository permissions."
            )
        return RepositoryPermissions(
            allow_push=trans.app.security_agent.usernames_that_can_push(repository),
            can_manage=can_manage_repo(trans, repository),
            can_push=can_update_repo(trans, repository),
        )

    @router.get(
        "/api/repositories/{encoded_repository_id}/allow_push",
        operation_id="repositories__show_allow_push",
    )
    def show_allow_push(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_repository_id: str = RepositoryIdPathParam,
    ) -> List[str]:
        repository = get_repository_in_tool_shed(self.app, encoded_repository_id)
        ensure_can_manage(trans, repository)
        return trans.app.security_agent.usernames_that_can_push(repository)

    @router.post(
        "/api/repositories/{encoded_repository_id}/allow_push/{username}",
        operation_id="repositories__add_allow_push",
    )
    def add_allow_push(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_repository_id: str = RepositoryIdPathParam,
        username: str = UsernameIdPathParam,
    ) -> List[str]:
        repository = get_repository_in_tool_shed(self.app, encoded_repository_id)
        if not can_manage_repo(trans, repository):
            raise InsufficientPermissionsException("You do not have permission to update this repository.")
        repository.set_allow_push([username])
        return trans.app.security_agent.usernames_that_can_push(repository)

    @router.put(
        "/api/repositories/{encoded_repository_id}/revisions/{changeset_revision}/malicious",
        operation_id="repositories__set_malicious",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def set_malicious(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_repository_id: str = RepositoryIdPathParam,
        changeset_revision: str = ChangesetRevisionPathParam,
    ):
        repository_metadata = get_repository_metadata_for_management(trans, encoded_repository_id, changeset_revision)
        repository_metadata.malicious = True
        trans.sa_session.add(repository_metadata)
        trans.sa_session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.delete(
        "/api/repositories/{encoded_repository_id}/revisions/{changeset_revision}/malicious",
        operation_id="repositories__unset_malicious",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def unset_malicious(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_repository_id: str = RepositoryIdPathParam,
        changeset_revision: str = ChangesetRevisionPathParam,
    ):
        repository_metadata = get_repository_metadata_for_management(trans, encoded_repository_id, changeset_revision)
        repository_metadata.malicious = False
        trans.sa_session.add(repository_metadata)
        trans.sa_session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(
        "/api/repositories/{encoded_repository_id}/deprecated",
        operation_id="repositories__set_deprecated",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def set_deprecated(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_repository_id: str = RepositoryIdPathParam,
    ):
        repository = get_repository_in_tool_shed(self.app, encoded_repository_id)
        ensure_can_manage(trans, repository)
        repository.deprecated = True
        trans.sa_session.add(repository)
        trans.sa_session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.delete(
        "/api/repositories/{encoded_repository_id}/deprecated",
        operation_id="repositories__unset_deprecated",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def unset_deprecated(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_repository_id: str = RepositoryIdPathParam,
    ):
        repository = get_repository_in_tool_shed(self.app, encoded_repository_id)
        ensure_can_manage(trans, repository)
        repository.deprecated = False
        trans.sa_session.add(repository)
        trans.sa_session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.delete(
        "/api/repositories/{encoded_repository_id}/allow_push/{username}",
        operation_id="repositories__remove_allow_push",
    )
    def remove_allow_push(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_repository_id: str = RepositoryIdPathParam,
        username: str = UsernameIdPathParam,
    ) -> List[str]:
        repository = get_repository_in_tool_shed(self.app, encoded_repository_id)
        if not can_manage_repo(trans, repository):
            raise InsufficientPermissionsException("You do not have permission to update this repository.")
        repository.set_allow_push(None, remove_auth=username)
        return trans.app.security_agent.usernames_that_can_push(repository)

    @router.post(
        "/api/repositories/{encoded_repository_id}/changeset_revision",
        description="upload new revision to the repository",
        operation_id="repositories__create_revision",
    )
    async def create_changeset_revision(
        self,
        request: Request,
        encoded_repository_id: str = RepositoryIdPathParam,
        commit_message: Optional[str] = CommitMessageQueryParam,
        trans: SessionRequestContext = DependsOnTrans,
        files: Optional[List[UploadFile]] = None,
        revision_request: RepositoryUpdateRequest = Depends(RepositoryUpdateRequestFormData.as_form),  # type: ignore[attr-defined]
    ) -> RepositoryUpdate:
        try:
            # Code stolen from Marius' work in Galaxy's Tools API.

            files2: List[StarletteUploadFile] = cast(List[StarletteUploadFile], files or [])
            # FastAPI's UploadFile is a very light wrapper around starlette's UploadFile
            if not files2:
                data = await request.form()
                for value in data.values():
                    if isinstance(value, StarletteUploadFile):
                        files2.append(value)

            repository = get_repository_in_tool_shed(self.app, encoded_repository_id)

            if not can_update_repo(trans, repository):
                raise InsufficientPermissionsException("You do not have permission to update this repository.")

            assert trans.user
            assert files2
            the_file = files2[0]
            with tempfile.NamedTemporaryFile(
                dir=trans.app.config.new_file_path, prefix="upload_file_data_", delete=False
            ) as dest:
                upload_file_like: IO[bytes] = the_file.file
                shutil.copyfileobj(upload_file_like, dest)
            the_file.file.close()
            filename = dest.name
            try:
                message = upload_tar_and_set_metadata(
                    trans,
                    trans.request.host,
                    repository,
                    filename,
                    commit_message or revision_request.commit_message or "Uploaded",
                )
                return RepositoryUpdate(root=ValidRepostiroyUpdateMessage(message=message))
            finally:
                if os.path.exists(filename):
                    os.remove(filename)
        except Exception:
            import logging

            log = logging.getLogger(__name__)
            log.exception("Problem in here...")
            raise

    @router.get(
        "/api/repositories/{encoded_repository_id}/revisions/{changeset_revision}/readmes",
        description="fetch readmes for repository revision",
        operation_id="repositories__readmes",
        response_model=RepositoryRevisionReadmes,
    )
    def get_readmes(
        self,
        encoded_repository_id: str = RepositoryIdPathParam,
        changeset_revision: str = ChangesetRevisionPathParam,
    ) -> dict:
        repository = get_repository_in_tool_shed(self.app, encoded_repository_id)
        return readmes(self.app, repository, changeset_revision)

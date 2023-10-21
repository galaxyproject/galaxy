"""
API operations on remote files.
"""
import logging
from typing import (
    List,
    Optional,
)

from fastapi import Body
from fastapi.param_functions import Query
from typing_extensions import Annotated

from galaxy.files.sources import PluginKind
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.remote_files import RemoteFilesManager
from galaxy.schema.remote_files import (
    AnyRemoteFilesListResponse,
    CreatedEntryResponse,
    CreateEntryPayload,
    FilesSourcePluginList,
    RemoteFilesDisableMode,
    RemoteFilesFormat,
    RemoteFilesTarget,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["remote files"])

TargetQueryParam: str = Query(
    default=RemoteFilesTarget.ftpdir,
    title="Target source",
    description=("The source to load datasets from." " Possible values: ftpdir, userdir, importdir"),
)

FormatQueryParam: Optional[RemoteFilesFormat] = Query(
    default=RemoteFilesFormat.uri,
    title="Response format",
    description=(
        "The requested format of returned data. Either `flat` to simply list all the files"
        ", `jstree` to get a tree representation of the files, or the default `uri` to list "
        "files and directories by their URI."
    ),
)

RecursiveQueryParam: Optional[bool] = Query(
    default=None,
    title="Recursive",
    description=(
        "Wether to recursively lists all sub-directories." " This will be `True` by default depending on the `target`."
    ),
)

DisableModeQueryParam: Optional[RemoteFilesDisableMode] = Query(
    default=None,
    title="Disable mode",
    description=(
        "(This only applies when `format` is `jstree`)"
        " The value can be either `folders` or `files` and it will disable the"
        " corresponding nodes of the tree."
    ),
)

WriteableQueryParam: Optional[bool] = Query(
    default=None,
    title="Writeable",
    description=(
        "Whether the query is made with the intention of writing to the source."
        " If set to True, only entries that can be written to will be returned."
    ),
)

BrowsableQueryParam: Optional[bool] = Query(
    default=True,
    title="Browsable filesources only",
    description=(
        "Whether to return browsable filesources only. The default is `True`, which will omit filesources"
        "like `http` and `base64` that do not implement a list method."
    ),
)

IncludeKindQueryParam = Query(
    title="Include kind",
    description=(
        "Whether to return **only** filesources of the specified kind. The default is `None`, which will return"
        " all filesources. Multiple values can be specified by repeating the parameter."
    ),
)

ExcludeKindQueryParam = Query(
    title="Exclude kind",
    description=(
        "Whether to exclude filesources of the specified kind from the list. The default is `None`, which will return"
        " all filesources. Multiple values can be specified by repeating the parameter."
    ),
)


@router.cbv
class FastAPIRemoteFiles:
    manager: RemoteFilesManager = depends(RemoteFilesManager)

    @router.get(
        "/api/remote_files",
        summary="Displays remote files available to the user.",
        response_description="A list with details about the remote files available to the user.",
    )
    @router.get(
        "/api/ftp_files",
        deprecated=True,
        summary="Displays remote files available to the user. Please use /api/remote_files instead.",
    )
    async def index(
        self,
        user_ctx: ProvidesUserContext = DependsOnTrans,
        target: str = TargetQueryParam,
        format: Optional[RemoteFilesFormat] = FormatQueryParam,
        recursive: Optional[bool] = RecursiveQueryParam,
        disable: Optional[RemoteFilesDisableMode] = DisableModeQueryParam,
        writeable: Optional[bool] = WriteableQueryParam,
    ) -> AnyRemoteFilesListResponse:
        """Lists all remote files available to the user from different sources."""
        return self.manager.index(user_ctx, target, format, recursive, disable, writeable)

    @router.get(
        "/api/remote_files/plugins",
        summary="Display plugin information for each of the gxfiles:// URI targets available.",
        response_description="A list with details about each plugin.",
    )
    async def plugins(
        self,
        user_ctx: ProvidesUserContext = DependsOnTrans,
        browsable_only: Optional[bool] = BrowsableQueryParam,
        include_kind: Annotated[Optional[List[PluginKind]], IncludeKindQueryParam] = None,
        exclude_kind: Annotated[Optional[List[PluginKind]], ExcludeKindQueryParam] = None,
    ) -> FilesSourcePluginList:
        """Display plugin information for each of the gxfiles:// URI targets available."""
        return self.manager.get_files_source_plugins(
            user_ctx,
            browsable_only,
            set(include_kind) if include_kind else None,
            set(exclude_kind) if exclude_kind else None,
        )

    @router.post(
        "/api/remote_files",
        summary="Creates a new entry (directory/record) on the remote files source.",
    )
    async def create_entry(
        self,
        user_ctx: ProvidesUserContext = DependsOnTrans,
        payload: CreateEntryPayload = Body(
            ...,
            title="Entry Data",
            description="Information about the entry to create. Depends on the target file source.",
        ),
    ) -> CreatedEntryResponse:
        """Creates a new entry on the remote files source."""
        return self.manager.create_entry(user_ctx, payload)

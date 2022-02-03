"""
API operations on remote files.
"""
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from fastapi.param_functions import Query

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.remote_files import RemoteFilesManager
from galaxy.schema.remote_files import (
    FilesSourcePluginList,
    RemoteFilesDisableMode,
    RemoteFilesFormat,
    RemoteFilesTarget,
)
from galaxy.web import expose_api
from . import (
    BaseGalaxyAPIController,
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


@router.cbv
class FastAPIRemoteFiles:
    manager: RemoteFilesManager = depends(RemoteFilesManager)

    @router.get(
        "/api/remote_files",
        summary="Displays remote files available to the user.",
        response_description="A list with details about the remote files available to the user.",
    )
    async def index(
        self,
        user_ctx: ProvidesUserContext = DependsOnTrans,
        target: str = TargetQueryParam,
        format: Optional[RemoteFilesFormat] = FormatQueryParam,
        recursive: Optional[bool] = RecursiveQueryParam,
        disable: Optional[RemoteFilesDisableMode] = DisableModeQueryParam,
    ) -> List[Dict[str, Any]]:
        """Lists all remote files available to the user from different sources."""
        return self.manager.index(user_ctx, target, format, recursive, disable)

    @router.get(
        "/api/remote_files/plugins",
        summary="Display plugin information for each of the gxfiles:// URI targets available.",
        response_description="A list with details about each plugin.",
    )
    async def plugins(
        self,
        user_ctx: ProvidesUserContext = DependsOnTrans,
    ) -> FilesSourcePluginList:
        """Display plugin information for each of the gxfiles:// URI targets available."""
        return self.manager.get_files_source_plugins(user_ctx)


class RemoteFilesAPIController(BaseGalaxyAPIController):
    manager: RemoteFilesManager = depends(RemoteFilesManager)

    @expose_api
    def index(self, trans: ProvidesUserContext, **kwd):
        """
        GET /api/remote_files/

        Displays remote files.

        :param  target:      target to load available datasets from, defaults to ftpdir
            possible values: ftpdir, userdir, importdir
        :type   target:      str

        :param  format:      requested format of data, defaults to flat
            possible values: flat, jstree

        :returns:   list of available files
        :rtype:     list
        """
        # If set, target must be one of 'ftpdir' (default), 'userdir', 'importdir'
        target = kwd.get("target", "ftpdir")
        format = kwd.get("format", None)
        recursive = kwd.get("recursive", None)
        disable = kwd.get("disable", None)

        return self.manager.index(trans, target, format, recursive, disable)

    @expose_api
    def plugins(self, trans: ProvidesUserContext, **kwd):
        """
        GET /api/remote_files/plugins

        Display plugin information for each of the gxfiles:// URI targets available.

        :returns:   list of configured plugins
        :rtype:     list
        """
        return self.manager.get_files_source_plugins(trans)

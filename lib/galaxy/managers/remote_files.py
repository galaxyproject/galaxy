
import hashlib
from operator import itemgetter
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pydantic.tools import parse_obj_as

from galaxy import exceptions
from galaxy.app import StructuredApp
from galaxy.files import (
    ConfiguredFileSources,
    ProvidesUserFileSourcesUserContext,
)
from galaxy.files._schema import (
    FilesSourcePluginList,
    RemoteFilesDisableMode,
    RemoteFilesFormat,
    RemoteFilesTarget,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.util import (
    jstree,
    smart_str,
)


class RemoteFilesManager:
    """
    Interface/service object for interacting with remote files.
    """

    def __init__(self, app: StructuredApp):
        self._app = app

    def index(
        self,
        user_ctx: ProvidesUserContext,
        target: str,
        format: Optional[RemoteFilesFormat],
        recursive: Optional[bool],
        disable: Optional[RemoteFilesDisableMode],
    ) -> List[Dict[str, Any]]:
        """Returns a list of remote files available to the user."""

        user_file_source_context = ProvidesUserFileSourcesUserContext(user_ctx)
        default_recursive = False
        default_format = RemoteFilesFormat.uri

        if "://" in target:
            uri = target
        elif target == RemoteFilesTarget.userdir:
            uri = "gxuserimport://"
            default_format = RemoteFilesFormat.flat
            default_recursive = True
        elif target == RemoteFilesTarget.importdir:
            uri = 'gximport://'
            default_format = RemoteFilesFormat.flat
            default_recursive = True
        elif target in [RemoteFilesTarget.ftpdir, 'ftp']:  # legacy, allow both
            uri = 'gxftp://'
            default_format = RemoteFilesFormat.flat
            default_recursive = True
        else:
            raise exceptions.RequestParameterInvalidException(f"Invalid target parameter supplied [{target}]")

        if format is None:
            format = default_format

        if recursive is None:
            recursive = default_recursive

        self._file_sources.validate_uri_root(uri, user_context=user_file_source_context)

        file_source_path = self._file_sources.get_file_source_path(uri)
        file_source = file_source_path.file_source
        index = file_source.list(file_source_path.path, recursive=recursive, user_context=user_file_source_context)
        if format == RemoteFilesFormat.flat:
            # rip out directories, ensure sorted by path
            index = [i for i in index if i["class"] == "File"]
            index = sorted(index, key=itemgetter("path"))
        if format == RemoteFilesFormat.jstree:
            if disable is None:
                disable = RemoteFilesDisableMode.folders

            jstree_paths = []
            for ent in index:
                path = ent["path"]
                path_hash = hashlib.sha1(smart_str(path)).hexdigest()
                if ent["class"] == "Directory":
                    path_type = 'folder'
                    disabled = True if disable == RemoteFilesDisableMode.folders else False
                else:
                    path_type = 'file'
                    disabled = True if disable == RemoteFilesDisableMode.files else False

                jstree_paths.append(jstree.Path(path, path_hash, {'type': path_type, 'state': {'disabled': disabled}, 'li_attr': {'full_path': path}}))
            userdir_jstree = jstree.JSTree(jstree_paths)
            index = userdir_jstree.jsonData()

        return index

    def get_files_source_plugins(self) -> FilesSourcePluginList:
        """Display plugin information for each of the gxfiles:// URI targets available."""
        plugins = self._file_sources.plugins_to_dict()
        return parse_obj_as(FilesSourcePluginList, plugins)

    @property
    def _file_sources(self) -> ConfiguredFileSources:
        return self._app.file_sources

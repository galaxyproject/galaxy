from typing import (
    Optional,
    Union,
)

from fs.osfs import OSFS

from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    FilesSourceRuntimeContext,
)
from galaxy.util.config_templates import TemplateExpansion
from ._fsspec import (
    FsspecFilesSource,
    FsspecFilesSourceProperties,
)


class TempFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    root_path: Union[str, TemplateExpansion]


class TempFileSourceConfiguration(BaseFileSourceConfiguration):
    root_path: str


class TempFilesSource(FsspecFilesSource[TempFileSourceTemplateConfiguration, TempFileSourceConfiguration]):
    """A FilesSource plugin for temporary file systems.

    Used for testing and other temporary file system needs.

    Note: This plugin is not intended for production use.
    """

    plugin_type = "temp"
    required_module = LocalFileSystem
    required_package = "fsspec"

    template_config_class = TempFileSourceTemplateConfiguration
    resolved_config_class = TempFileSourceConfiguration

    def _open_fs(self, context: FilesSourceRuntimeContext[TempFileSourceConfiguration]):
        if OSFS is None:
            raise self.required_package_exception

        return OSFS(root_path=context.config.root_path)

    def __init__(self, **kwd: Unpack[FsspecFilesSourceProperties]):
        super().__init__(**kwd)
        props = self._parse_common_config_opts(kwd)
        self._root_path = props.get("root_path", "")

    def _ensure_root_path(self):
        if not self._root_path:
            raise ValueError("The config value for 'root_path' must be set for TempFilesSource.")

    def _to_temp_path(self, path: str) -> str:
        """Convert a virtual temp path to an actual filesystem path."""
        self._ensure_root_path()

        relative_path = path.lstrip(os.sep)
        if not relative_path:
            return self._root_path
        return os.path.join(self._root_path, relative_path)

    def _from_temp_path(self, native_path: str) -> str:
        """Convert an actual filesystem path back to virtual temp path."""
        self._ensure_root_path()
        native_path = native_path.replace(self._root_path, os.sep, 1)
        return native_path

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = self._serialization_props(user_context)
        extra_props = opts.extra_props or {} if opts else {}

        root_path = props.pop("root_path", None)
        if root_path is None:
            root_path = tempfile.mkdtemp()

        self._root_path = root_path
        handle = LocalFileSystem(auto_mkdir=True, **{**props, **extra_props})
        return handle

    def _list(
        self,
        path="/",
        recursive=False,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Tuple[List[AnyRemoteEntry], int]:
        native_path = self._to_temp_path(path)
        entries, total = super()._list(
            path=native_path,
            recursive=recursive,
            user_context=user_context,
            opts=opts,
            limit=limit,
            offset=offset,
            query=query,
            sort_by=sort_by,
        )

        # Transform the paths in the results back to virtual paths
        for entry in entries:
            entry["path"] = self._from_temp_path(entry["path"])
            entry["uri"] = self._from_temp_path(entry["uri"])

        return entries, total

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        temp_path = self._to_temp_path(source_path)
        return super()._realize_to(temp_path, native_path, user_context, opts)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        temp_path = self._to_temp_path(target_path)
        return super()._write_from(temp_path, native_path, user_context, opts)

    def get_scheme(self) -> str:
        return "temp"


__all__ = ("TempFilesSource",)

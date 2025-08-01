import functools
import os
import shutil
from typing import (
    Any,
    ClassVar,
    Optional,
)

from galaxy import exceptions
from galaxy.files import OptionalUserContext
from galaxy.util.path import (
    safe_contains,
    safe_path,
    safe_walk,
)
from . import (
    AnyRemoteEntry,
    BaseFilesSource,
    FilesSourceOptions,
    FilesSourceProperties,
    RemoteDirectory,
    RemoteFile,
)

DEFAULT_ENFORCE_SYMLINK_SECURITY = True
DEFAULT_DELETE_ON_REALIZE = False
DEFAULT_ALLOW_SUBDIR_CREATION = True
DEFAULT_PREFER_LINKS = False


class PosixFileSourceConfiguration(FilesSourceProperties):
    root: Optional[str] = None
    enforce_symlink_security: bool = DEFAULT_ENFORCE_SYMLINK_SECURITY
    delete_on_realize: bool = DEFAULT_DELETE_ON_REALIZE
    allow_subdir_creation: bool = DEFAULT_ALLOW_SUBDIR_CREATION
    prefer_links: bool = DEFAULT_PREFER_LINKS


class PosixFilesSource(BaseFilesSource):
    plugin_type = "posix"
    config_class: ClassVar[type[PosixFileSourceConfiguration]] = PosixFileSourceConfiguration
    config: PosixFileSourceConfiguration

    # If this were a PyFilesystem2FilesSource all that would be needed would be,
    # but we couldn't enforce security our way I suspect.
    # def _open_fs(self):
    #    from fs.osfs import OSFS
    #    handle = OSFS(**self._props)
    #    return handle

    def __init__(self, config: PosixFileSourceConfiguration):
        super().__init__(config)

        if not self.config.root:
            self.config.writable = False

    def _list(
        self,
        path="/",
        recursive=True,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        self.update_config_from_options(opts, user_context)
        if not self.config.root:
            raise exceptions.ItemAccessibilityException("Listing files at file:// URLs has been disabled.")
        dir_path = self._to_native_path(path, user_context=user_context)
        if not self._safe_directory(dir_path):
            raise exceptions.ObjectNotFound(f"The specified directory does not exist [{dir_path}].")
        if recursive:
            res: list[AnyRemoteEntry] = []
            effective_root = self._effective_root(user_context)
            for p, dirs, files in safe_walk(dir_path, allowlist=self._allowlist):
                rel_dir = os.path.relpath(p, effective_root)
                to_dict = functools.partial(self._resource_info_to_dict, rel_dir, user_context=user_context)
                res.extend(map(to_dict, dirs))
                res.extend(map(to_dict, files))
            return res, len(res)
        else:
            entry_names = os.listdir(dir_path)
            to_dict = functools.partial(self._resource_info_to_dict, path, user_context=user_context)
            return list(map(to_dict, entry_names)), len(entry_names)

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        self.update_config_from_options(opts, user_context)
        if not self.config.root and (not user_context or not user_context.is_admin):
            raise exceptions.ItemAccessibilityException("Writing to file:// URLs has been disabled.")

        effective_root = self._effective_root(user_context)
        source_native_path = self._to_native_path(source_path, user_context=user_context)
        if self.config.enforce_symlink_security:
            if not safe_contains(effective_root, source_native_path, allowlist=self._allowlist):
                raise Exception("Operation not allowed.")
        else:
            source_native_path = os.path.normpath(source_native_path)
            assert source_native_path.startswith(os.path.normpath(effective_root))

        if not self.config.delete_on_realize:
            shutil.copyfile(source_native_path, native_path)
        else:
            shutil.move(source_native_path, native_path)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        self.update_config_from_options(opts, user_context)
        effective_root = self._effective_root(user_context)
        target_native_path = self._to_native_path(target_path, user_context=user_context)
        if self.config.enforce_symlink_security:
            if not safe_contains(effective_root, target_native_path, allowlist=self._allowlist):
                raise Exception("Operation not allowed.")
        else:
            target_native_path = os.path.normpath(target_native_path)
            assert target_native_path.startswith(os.path.normpath(effective_root))

        target_native_path_parent, target_native_path_name = os.path.split(target_native_path)
        if not os.path.exists(target_native_path_parent):
            if self.config.allow_subdir_creation:
                os.makedirs(target_native_path_parent)
            else:
                raise Exception("Parent directory does not exist.")

        # Use a temporary name while writing so anything that consumes written files can detect when they've completed,
        # and identify interrupted writes
        target_native_path_part = os.path.join(target_native_path_parent, f"_{target_native_path_name}.part")
        shutil.copyfile(native_path, target_native_path_part)
        os.rename(target_native_path_part, target_native_path)

    def _to_native_path(self, source_path: str, user_context: OptionalUserContext = None):
        source_path = os.path.normpath(source_path)
        if source_path.startswith("/"):
            source_path = source_path[1:]
        return os.path.join(self._effective_root(user_context), source_path)

    def _effective_root(self, user_context: OptionalUserContext = None) -> str:
        return str(self._evaluate_prop(self.config.root or "/", user_context=user_context))

    def _resource_info_to_dict(self, dir: str, name: str, user_context: OptionalUserContext = None) -> AnyRemoteEntry:
        rel_path = os.path.normpath(os.path.join(dir, name))
        full_path = self._to_native_path(rel_path, user_context=user_context)
        uri = self.uri_from_path(rel_path)
        if os.path.isdir(full_path):
            return RemoteDirectory(name=name, uri=uri, path=rel_path)
        else:
            file_stat_info = os.lstat(full_path)
            return RemoteFile(
                name=name,
                size=file_stat_info.st_size,
                ctime=self.to_dict_time(file_stat_info.st_ctime),
                uri=uri,
                path=rel_path,
            )

    def _safe_directory(self, directory: str) -> bool:
        if self.config.enforce_symlink_security:
            if not safe_path(directory, allowlist=self._allowlist):
                raise exceptions.ConfigDoesNotAllowException(
                    f"directory ({directory}) is a symlink to a location not on the allowlist"
                )

        if not os.path.exists(directory):
            return False
        return True

    def _serialization_props(self, user_context: OptionalUserContext = None) -> dict[str, Any]:
        return {
            # abspath needed because will be used by external Python from
            # a job working directory
            "root": os.path.abspath(self._effective_root(user_context)),
            "enforce_symlink_security": self.config.enforce_symlink_security,
            "delete_on_realize": self.config.delete_on_realize,
            "allow_subdir_creation": self.config.allow_subdir_creation,
            "prefer_links": self.config.prefer_links,
        }

    @property
    def _allowlist(self):
        return self._file_sources_config.symlink_allowlist

    def score_url_match(self, url: str):
        # For security, we need to ensure that a partial match doesn't work. e.g. file://{root}something/myfiles
        if self.config.root and (
            url.startswith(f"{self.get_uri_root()}://{self.config.root}/")
            or url == f"self.get_uri_root()://{self.config.root}"
        ):
            return len(f"self.get_uri_root()://{self.config.root}")
        elif self.config.root and (
            url.startswith(f"file://{self.config.root}/") or url == f"file://{self.config.root}"
        ):
            return len(f"file://{self.config.root}")
        elif not self.config.root and url.startswith("file://"):
            return len("file://")
        else:
            return super().score_url_match(url)

    def to_relative_path(self, url: str) -> str:
        if url.startswith(f"file://{self.config.root}"):
            return url[len(f"file://{self.config.root}") :]
        elif url.startswith("file://"):
            return url[7:]
        else:
            return super().to_relative_path(url)


__all__ = ("PosixFilesSource",)

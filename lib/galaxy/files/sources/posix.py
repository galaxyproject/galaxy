import functools
import os
import shutil
from typing import (
    Any,
    Optional,
    Union,
)

from galaxy import exceptions
from galaxy.files.models import (
    AnyRemoteEntry,
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.util.config_templates import TemplateExpansion
from galaxy.util.path import (
    safe_contains,
    safe_path,
    safe_walk,
)
from . import BaseFilesSource

DEFAULT_ENFORCE_SYMLINK_SECURITY = True
DEFAULT_DELETE_ON_REALIZE = False
DEFAULT_ALLOW_SUBDIR_CREATION = True
DEFAULT_PREFER_LINKS = False


class PosixTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    """Posix template configuration with templating support."""

    root: Union[str, TemplateExpansion, None] = None
    # These are not using TemplateExpansion because they are not user-configurable.
    enforce_symlink_security: bool = DEFAULT_ENFORCE_SYMLINK_SECURITY
    delete_on_realize: bool = DEFAULT_DELETE_ON_REALIZE
    allow_subdir_creation: bool = DEFAULT_ALLOW_SUBDIR_CREATION
    prefer_links: bool = DEFAULT_PREFER_LINKS


class PosixConfiguration(BaseFileSourceConfiguration):
    """Posix resolved configuration with proper types."""

    root: Optional[str] = None
    enforce_symlink_security: bool = DEFAULT_ENFORCE_SYMLINK_SECURITY
    delete_on_realize: bool = DEFAULT_DELETE_ON_REALIZE
    allow_subdir_creation: bool = DEFAULT_ALLOW_SUBDIR_CREATION
    prefer_links: bool = DEFAULT_PREFER_LINKS


class PosixFilesSource(BaseFilesSource[PosixTemplateConfiguration, PosixConfiguration]):
    plugin_type = "posix"

    template_config_class = PosixTemplateConfiguration
    resolved_config_class = PosixConfiguration

    # If this were a PyFilesystem2FilesSource it would be much simpler,
    # but we couldn't enforce security our way I suspect.

    def __init__(self, template_config: PosixTemplateConfiguration):
        super().__init__(template_config)
        if not self.template_config.root:
            self.template_config.writable = False

    def prefer_links(self) -> bool:
        return self.template_config.prefer_links

    @property
    def root(self) -> Optional[str]:
        """Return the root directory for backward compatibility."""
        return self.template_config.root

    def _list(
        self,
        context: FilesSourceRuntimeContext[PosixConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        if not context.config.root:
            raise exceptions.ItemAccessibilityException("Listing files at file:// URLs has been disabled.")
        dir_path = self._to_native_path(path, context.config)
        if not self._safe_directory(dir_path, context.config):
            raise exceptions.ObjectNotFound(f"The specified directory does not exist [{dir_path}].")
        if recursive:
            res: list[AnyRemoteEntry] = []
            effective_root = self._effective_root(context.config)
            for p, dirs, files in safe_walk(dir_path, allowlist=self._allowlist):
                rel_dir = os.path.relpath(p, effective_root)
                to_dict = functools.partial(self._resource_info_to_dict, rel_dir, config=context.config)
                res.extend(map(to_dict, dirs))
                res.extend(map(to_dict, files))
            return res, len(res)
        else:
            entry_names = os.listdir(dir_path)
            to_dict = functools.partial(self._resource_info_to_dict, path, config=context.config)
            return list(map(to_dict, entry_names)), len(entry_names)

    def _realize_to(self, source_path: str, native_path: str, context: FilesSourceRuntimeContext[PosixConfiguration]):
        if not context.config.root and not context.user_data.is_admin:
            raise exceptions.ItemAccessibilityException("Writing to file:// URLs has been disabled.")

        effective_root = self._effective_root(context.config)
        source_native_path = self._to_native_path(source_path, context.config)
        if context.config.enforce_symlink_security:
            if not safe_contains(effective_root, source_native_path, allowlist=self._allowlist):
                raise Exception("Operation not allowed.")
        else:
            source_native_path = os.path.normpath(source_native_path)
            assert source_native_path.startswith(os.path.normpath(effective_root))

        if not context.config.delete_on_realize:
            shutil.copyfile(source_native_path, native_path)
        else:
            shutil.move(source_native_path, native_path)

    def _write_from(self, target_path: str, native_path: str, context: FilesSourceRuntimeContext[PosixConfiguration]):
        effective_root = self._effective_root(context.config)
        target_native_path = self._to_native_path(target_path, context.config)
        if context.config.enforce_symlink_security:
            if not safe_contains(effective_root, target_native_path, allowlist=self._allowlist):
                raise Exception("Operation not allowed.")
        else:
            target_native_path = os.path.normpath(target_native_path)
            assert target_native_path.startswith(os.path.normpath(effective_root))

        target_native_path_parent, target_native_path_name = os.path.split(target_native_path)
        if not os.path.exists(target_native_path_parent):
            if context.config.allow_subdir_creation:
                os.makedirs(target_native_path_parent)
            else:
                raise Exception("Parent directory does not exist.")

        # Use a temporary name while writing so anything that consumes written files can detect when they've completed,
        # and identify interrupted writes
        target_native_path_part = os.path.join(target_native_path_parent, f"_{target_native_path_name}.part")
        shutil.copyfile(native_path, target_native_path_part)
        os.rename(target_native_path_part, target_native_path)

    def _to_native_path(self, source_path: str, config: PosixConfiguration):
        source_path = os.path.normpath(source_path)
        if source_path.startswith("/"):
            source_path = source_path[1:]
        return os.path.join(self._effective_root(config), source_path)

    def _effective_root(self, config: PosixConfiguration) -> str:
        return config.root or "/"

    def _resource_info_to_dict(self, dir: str, name: str, config: PosixConfiguration) -> AnyRemoteEntry:
        rel_path = os.path.normpath(os.path.join(dir, name))
        full_path = self._to_native_path(rel_path, config)
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

    def _safe_directory(self, directory: str, config: PosixConfiguration) -> bool:
        if config.enforce_symlink_security:
            if not safe_path(directory, allowlist=self._allowlist):
                raise exceptions.ConfigDoesNotAllowException(
                    f"directory ({directory}) is a symlink to a location not on the allowlist"
                )

        if not os.path.exists(directory):
            return False
        return True

    def _serialize_config(self, config: PosixConfiguration) -> dict[str, Any]:
        # abspath needed because will be used by external Python from
        # a job working directory
        abs_root = os.path.abspath(self._effective_root(config))
        serialized_config = super()._serialize_config(config)
        serialized_config.update({"root": abs_root})
        return serialized_config

    @property
    def _allowlist(self):
        return self._file_sources_config.symlink_allowlist

    def score_url_match(self, url: str):
        # We need to use template_config here because this is called before the template is expanded.
        root = self.template_config.root
        # For security, we need to ensure that a partial match doesn't work. e.g. file://{root}something/myfiles
        if root and (url.startswith(f"{self.get_uri_root()}://{root}/") or url == f"self.get_uri_root()://{root}"):
            return len(f"self.get_uri_root()://{root}")
        elif root and (url.startswith(f"file://{root}/") or url == f"file://{root}"):
            return len(f"file://{root}")
        elif not root and url.startswith("file://"):
            return len("file://")
        else:
            return super().score_url_match(url)

    def to_relative_path(self, url: str) -> str:
        # We need to use template_config.root here because this is called before the template is expanded.
        root = self.template_config.root
        if url.startswith(f"file://{root}"):
            return url[len(f"file://{root}") :]
        elif url.startswith("file://"):
            return url[7:]
        else:
            return super().to_relative_path(url)


__all__ = ("PosixFilesSource",)

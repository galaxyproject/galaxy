import functools
import os
import shutil
from typing import (
    Any,
    Dict,
    List,
)

from galaxy import exceptions
from galaxy.util.path import (
    safe_contains,
    safe_path,
    safe_walk,
)
from ..sources import BaseFilesSource

DEFAULT_ENFORCE_SYMLINK_SECURITY = True
DEFAULT_DELETE_ON_REALIZE = False
DEFAULT_ALLOW_SUBDIR_CREATION = True


class PosixFilesSource(BaseFilesSource):
    plugin_type = "posix"

    # If this were a PyFilesystem2FilesSource all that would be needed would be,
    # but we couldn't enforce security our way I suspect.
    # def _open_fs(self):
    #    from fs.osfs import OSFS
    #    handle = OSFS(**self._props)
    #    return handle

    def __init__(self, **kwd):
        props = self._parse_common_config_opts(kwd)
        self.root = props["root"]
        self.enforce_symlink_security = props.get("enforce_symlink_security", DEFAULT_ENFORCE_SYMLINK_SECURITY)
        self.delete_on_realize = props.get("delete_on_realize", DEFAULT_DELETE_ON_REALIZE)
        self.allow_subdir_creation = props.get("allow_subdir_creation", DEFAULT_ALLOW_SUBDIR_CREATION)

    def _list(self, path="/", recursive=True, user_context=None):
        dir_path = self._to_native_path(path, user_context=user_context)
        if not self._safe_directory(dir_path):
            raise exceptions.ObjectNotFound(f"The specified directory does not exist [{dir_path}].")
        if recursive:
            res: List[Dict[str, Any]] = []
            effective_root = self._effective_root(user_context)
            for (p, dirs, files) in safe_walk(dir_path, allowlist=self._allowlist):
                rel_dir = os.path.relpath(p, effective_root)
                to_dict = functools.partial(self._resource_info_to_dict, rel_dir, user_context=user_context)
                res.extend(map(to_dict, dirs))
                res.extend(map(to_dict, files))
            return res
        else:
            res = os.listdir(dir_path)
            to_dict = functools.partial(self._resource_info_to_dict, path, user_context=user_context)
            return list(map(to_dict, res))

    def _realize_to(self, source_path, native_path, user_context=None):
        effective_root = self._effective_root(user_context)
        source_native_path = self._to_native_path(source_path, user_context=user_context)
        if self.enforce_symlink_security:
            if not safe_contains(effective_root, source_native_path, allowlist=self._allowlist):
                raise Exception("Operation not allowed.")
        else:
            source_native_path = os.path.normpath(source_native_path)
            assert source_native_path.startswith(os.path.normpath(effective_root))

        if not self.delete_on_realize:
            shutil.copyfile(source_native_path, native_path)
        else:
            shutil.move(source_native_path, native_path)

    def _write_from(self, target_path, native_path, user_context=None):
        effective_root = self._effective_root(user_context)
        target_native_path = self._to_native_path(target_path, user_context=user_context)
        if self.enforce_symlink_security:
            if not safe_contains(effective_root, target_native_path, allowlist=self._allowlist):
                raise Exception("Operation not allowed.")
        else:
            target_native_path = os.path.normpath(target_native_path)
            assert target_native_path.startswith(os.path.normpath(effective_root))

        target_native_path_parent = os.path.dirname(target_native_path)
        if not os.path.exists(target_native_path_parent):
            if self.allow_subdir_creation:
                os.makedirs(target_native_path_parent)
            else:
                raise Exception("Parent directory does not exist.")

        shutil.copyfile(native_path, target_native_path)

    def _to_native_path(self, source_path, user_context=None):
        source_path = os.path.normpath(source_path)
        if source_path.startswith("/"):
            source_path = source_path[1:]
        return os.path.join(self._effective_root(user_context), source_path)

    def _effective_root(self, user_context=None):
        return self._evaluate_prop(self.root, user_context=user_context)

    def _resource_info_to_dict(self, dir, name, user_context=None):
        rel_path = os.path.normpath(os.path.join(dir, name))
        full_path = self._to_native_path(rel_path, user_context=user_context)
        uri = self.uri_from_path(rel_path)
        if os.path.isdir(full_path):
            return {"class": "Directory", "name": name, "uri": uri, "path": rel_path}
        else:
            statinfo = os.lstat(full_path)
            return {
                "class": "File",
                "name": name,
                "size": statinfo.st_size,
                "ctime": self.to_dict_time(statinfo.st_ctime),
                "uri": uri,
                "path": rel_path,
            }

    def _safe_directory(self, directory):
        if self.enforce_symlink_security:
            if not safe_path(directory, allowlist=self._allowlist):
                raise exceptions.ConfigDoesNotAllowException(
                    f"directory ({directory}) is a symlink to a location not on the allowlist"
                )

        if not os.path.exists(directory):
            return False
        return True

    def _serialization_props(self, user_context=None):
        return {
            # abspath needed because will be used by external Python from
            # a job working directory
            "root": os.path.abspath(self._effective_root(user_context)),
            "enforce_symlink_security": self.enforce_symlink_security,
            "delete_on_realize": self.delete_on_realize,
            "allow_subdir_creation": self.allow_subdir_creation,
        }

    @property
    def _allowlist(self):
        return self._file_sources_config.symlink_allowlist


__all__ = ("PosixFilesSource",)

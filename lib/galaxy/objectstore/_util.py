import multiprocessing
import os
import subprocess

from galaxy.util import (
    umask_fix_perms,
    which,
)


def fix_permissions(config, rel_path: str):
    """Set permissions on rel_path"""
    for basedir, _, files in os.walk(rel_path):
        umask_fix_perms(basedir, config.umask, 0o777, config.gid)
        for filename in files:
            path = os.path.join(basedir, filename)
            # Ignore symlinks
            if os.path.islink(path):
                continue
            umask_fix_perms(path, config.umask, 0o666, config.gid)


class UsesAxel:
    use_axel: bool

    def _init_axel(self) -> None:
        if which("axel"):
            self.use_axel = True
        else:
            self.use_axel = False

    def _axel_download(self, url: str, path: str):
        ncores = multiprocessing.cpu_count()
        ret_code = subprocess.call(["axel", "-a", "-o", path, "-n", str(ncores), url])
        return ret_code == 0

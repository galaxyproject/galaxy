import os

from galaxy.util import umask_fix_perms


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

"""Abstractions for installing local software managed and required by Galaxy/galaxy-lib."""

import abc
import logging
import os

from galaxy.util.filelock import (
    FileLock,
    FileLockException,
)

log = logging.getLogger(__name__)


class InstallableContext(metaclass=abc.ABCMeta):
    """Represent a directory/configuration of something that can be installed."""

    @abc.abstractmethod
    def is_installed(self):
        """Return bool indicating if the configured software is installed."""

    @abc.abstractmethod
    def can_install(self):
        """Check preconditions for installation."""

    @property
    @abc.abstractmethod
    def installable_description(self):
        """Short description of thing being installed for log statements."""

    @property
    @abc.abstractmethod
    def parent_path(self):
        """Return parent path of the location the installable will be created within."""


def ensure_installed(installable_context, install_func, auto_init):
    """Make sure target is installed - handle multiple processes potentially attempting installation."""
    parent_path = installable_context.parent_path
    desc = installable_context.installable_description

    def _check():
        if not installable_context.is_installed():
            if auto_init:
                if installable_context.can_install():
                    if install_func(installable_context):
                        installed = False
                        log.warning(f"{desc} installation requested and failed.")
                    else:
                        installed = installable_context.is_installed()
                        if not installed:
                            log.warning(f"{desc} installation requested, seemed to succeed, but not found.")
                else:
                    installed = False
            else:
                installed = False
                log.warning("%s not installed and auto-installation disabled.", desc)
        else:
            installed = True
        return installed

    if not os.path.lexists(parent_path):
        os.mkdir(parent_path)

    try:
        if auto_init and os.access(parent_path, os.W_OK):
            with FileLock(os.path.join(parent_path, desc.lower()), timeout=300):
                return _check()
        else:
            return _check()
    except FileLockException:
        raise Exception(f"Failed to get file lock for {os.path.join(parent_path, desc.lower())}")

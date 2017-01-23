"""Abstractions for installing local software managed and required by Galaxy/galaxy-lib."""

import logging
import os

from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)

from galaxy.util.filelock import (
    FileLock,
    FileLockException
)

log = logging.getLogger(__name__)


class InstallableContext(object):
    """Represent a directory/configuration of something that can be installed."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def is_installed(self):
        """Return bool indicating if the configured software is installed."""

    @abstractmethod
    def can_install(self):
        """Check preconditions for installation."""

    @abstractproperty
    def installable_description(self):
        """Short description of thing being installed for log statements."""

    @abstractproperty
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
                        log.warning("%s installation requested and failed." % desc)
                    else:
                        installed = installable_context.is_installed()
                        if not installed:
                            log.warning("%s installation requested, seemed to succeed, but not found." % desc)
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
            with FileLock(os.path.join(parent_path, desc.lower())):
                return _check()
        else:
            return _check()
    except FileLockException:
        return ensure_installed(installable_context, auto_init)

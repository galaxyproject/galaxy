"""
Interfaces to containerization software
"""

import logging
from abc import (
    ABCMeta,
    abstractmethod,
)

DEFAULT_CONTAINER_TYPE = "docker"
DEFAULT_CONF = {"_default_": {"type": DEFAULT_CONTAINER_TYPE}}

log = logging.getLogger(__name__)


class ContainerVolume(metaclass=ABCMeta):

    valid_modes = frozenset({"ro", "rw"})

    def __init__(self, path, host_path=None, mode=None):
        self.path = path
        self.host_path = host_path
        self.mode = mode
        if mode and not self.mode_is_valid:
            raise ValueError(f"Invalid container volume mode: {mode}")

    @abstractmethod
    def from_str(cls, as_str):
        """Classmethod to convert from this container type's string representation.

        :param  as_str: string representation of volume
        :type   as_str: str
        """

    @abstractmethod
    def __str__(self):
        """Return this container type's string representation of the volume."""

    @property
    def mode_is_valid(self):
        return self.mode in self.valid_modes

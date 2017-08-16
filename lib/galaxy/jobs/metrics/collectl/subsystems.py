"""Abstractions describing collectl subsystems (specified with the collectl ``-s`` parameter).

Subsystems are essentially monitoring plugins available within collectl.
"""
from abc import (
    ABCMeta,
    abstractmethod
)

import six


@six.add_metaclass(ABCMeta)
class CollectlSubsystem(object):
    """ Class providing an abstraction of collectl subsytems.
    """

    @property
    @abstractmethod
    def command_line_arg(self):
        """ Return single letter command-line argument used by collectl CLI.
        """

    @property
    @abstractmethod
    def name(self, job_directory):
        """ High-level name for subsystem as consumed by this module.
        """


class ProcessesSubsystem(CollectlSubsystem):
    command_line_arg = "Z"
    name = "process"


class CpuSubsystem(CollectlSubsystem):
    command_line_arg = "C"
    name = "cpu"


class DiskSubsystem(CollectlSubsystem):
    command_line_arg = "D"
    name = "disk"


class NetworkSubsystem(CollectlSubsystem):
    command_line_arg = "N"
    name = "network"


class EnvironmentSubsystem(CollectlSubsystem):
    command_line_arg = "E"
    name = "environment"


class MemorySubsystem(CollectlSubsystem):
    command_line_arg = "M"
    name = "memory"


SUBSYSTEMS = [
    ProcessesSubsystem(),
    CpuSubsystem(),
    DiskSubsystem(),
    NetworkSubsystem(),
    EnvironmentSubsystem(),
    MemorySubsystem(),
]
SUBSYSTEM_DICT = dict([(s.name, s) for s in SUBSYSTEMS])


def get_subsystem(name):
    """

    >>> get_subsystem( "process" ).command_line_arg == "Z"
    True
    """
    return SUBSYSTEM_DICT[name]


__all__ = ('get_subsystem', )

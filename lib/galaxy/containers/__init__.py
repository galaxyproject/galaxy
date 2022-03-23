"""
Interfaces to containerization software
"""

import logging
from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)
from typing import NamedTuple

DEFAULT_CONTAINER_TYPE = "docker"
DEFAULT_CONF = {"_default_": {"type": DEFAULT_CONTAINER_TYPE}}

log = logging.getLogger(__name__)


class ContainerPort(NamedTuple):
    """Named tuple representing ports published by a container, with attributes"""

    port: int  # Port number (inside the container)
    protocol: str  # Port protocol, either ``tcp`` or ``udp``
    hostaddr: str  # Address or hostname where the published port can be accessed
    hostport: int  # Published port number on which the container can be accessed


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


class Container(metaclass=ABCMeta):
    def __init__(self, interface, id, name=None, **kwargs):
        """

        :param      interface:  Container interface for the given container type
        :type       interface:  :class:`ContainerInterface` subclass instance
        :param      id:         Container identifier
        :type       id:         str
        :param      name:       Container name
        :type       name:       str

        """
        self._interface = interface
        self._id = id
        self._name = name

    @property
    def id(self):
        """The container's id"""
        return self._id

    @property
    def name(self):
        """The container's name"""
        return self._name

    @abstractmethod
    def from_id(cls, interface, id):
        """Classmethod to create an instance of Container from the container system's id for the given container type.

        :param  interface:  Container insterface for the given id
        :type   interface:  :class:`ContainerInterface` subclass instance
        :param  id:         Container identifier
        :type   id:         str
        :returns:           Container object
        :rtype:             :class:`Container` subclass instance
        """

    @abstractproperty
    def ports(self):
        """Attribute for accessing details of ports published by the container.

        :returns:   Port details
        :rtype:     list of :class:`ContainerPort` s
        """

    @abstractproperty
    def address(self):
        """Attribute for accessing the address or hostname where published ports can be accessed.

        :returns:   Hostname or IP address
        :rtype:     str
        """

    @abstractmethod
    def is_ready(self):
        """Indicate whether or not the container is "ready" (up, available, running).

        :returns:   True if ready, else False
        :rtpe:      bool
        """

    def map_port(self, port):
        """Map a given container port to a host address/port.

        For legacy reasons, if port is ``None``, the first port (if any) will be returned

        :param  port:   Container port to map
        :type   port:   int
        :returns:       Mapping to host address/port for given container port
        :rtype:         :class:`ContainerPort` instance
        """
        mapping = None
        ports = self.ports or []
        for mapping in ports:
            if port == mapping.port:
                return mapping
            if port is None:
                log.warning(
                    "Container %s (%s): Don't know how to map ports to containers with multiple exposed ports "
                    "when a specific port is not requested. Arbitrarily choosing first: %s",
                    self.name,
                    self.id,
                    mapping,
                )
                return mapping
        else:
            if port is None:
                log.warning("Container %s (%s): No exposed ports found!", self.name, self.id)
            else:
                log.warning("Container %s (%s): No mapping found for port: %s", self.name, self.id, port)
        return None

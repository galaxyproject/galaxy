"""
Model objects for docker objects
"""

import logging
import shlex

from galaxy.containers import (
    Container,
    ContainerPort,
    ContainerVolume,
)

log = logging.getLogger(__name__)


class DockerVolume(ContainerVolume):
    @classmethod
    def from_str(cls, as_str):
        """Construct an instance from a string as would be passed to `docker run --volume`.

        A string in the format ``<host_path>:<mode>`` is supported for legacy purposes even though it is not valid
        Docker volume syntax.
        """
        if not as_str:
            raise ValueError(f"Failed to parse Docker volume from {as_str}")
        parts = as_str.split(":", 2)
        kwds = dict(host_path=parts[0])
        if len(parts) == 1:
            # auto-generated volume
            kwds["path"] = kwds["host_path"]
        elif len(parts) == 2:
            # /host_path:mode is not (or is no longer?) valid Docker volume syntax
            if parts[1] in DockerVolume.valid_modes:
                kwds["mode"] = parts[1]
                kwds["path"] = kwds["host_path"]
            else:
                kwds["path"] = parts[1]
        elif len(parts) == 3:
            kwds["path"] = parts[1]
            kwds["mode"] = parts[2]
        return cls(**kwds)

    def __str__(self):
        volume_str = ":".join(filter(lambda x: x is not None, (self.host_path, self.path, self.mode)))
        if "$" not in volume_str:
            volume_for_cmd_line = shlex.quote(volume_str)
        else:
            # e.g. $_GALAXY_JOB_TMP_DIR:$_GALAXY_JOB_TMP_DIR:rw so don't single quote.
            volume_for_cmd_line = f'"{volume_str}"'
        return volume_for_cmd_line

    def to_native(self):
        host_path = self.host_path or self.path
        return (self.path, {host_path: {"bind": self.path, "mode": self.mode}})


class DockerContainer(Container):
    def __init__(self, interface, id, name=None, inspect=None):
        super().__init__(interface, id, name=name)
        self._inspect = inspect

    @classmethod
    def from_id(cls, interface, id):
        inspect = interface.inspect(id)
        return cls(interface, id, name=inspect["Name"], inspect=inspect)

    @property
    def ports(self):
        # {
        #     "NetworkSettings" : {
        #         "Ports" : {
        #             "3306/tcp" : [
        #                 {
        #                     "HostIp" : "127.0.0.1",
        #                     "HostPort" : "3306"
        #                 }
        #             ]
        rval = []
        try:
            port_mappings = self.inspect["NetworkSettings"]["Ports"]
        except KeyError:
            log.warning(
                "Failed to get ports for container %s from `docker inspect` output at "
                "['NetworkSettings']['Ports']: %s: %s",
                self.id,
                exc_info=True,
            )
            return None
        for port_name in port_mappings:
            for binding in port_mappings[port_name]:
                rval.append(
                    ContainerPort(
                        int(port_name.split("/")[0]),
                        port_name.split("/")[1],
                        self.address,
                        int(binding["HostPort"]),
                    )
                )
        return rval

    @property
    def address(self):
        if self._interface.host and self._interface.host.startswith("tcp://"):
            return self._interface.host.replace("tcp://", "").split(":", 1)[0]
        else:
            return "localhost"

    def is_ready(self):
        return self.inspect["State"]["Running"]

    def __eq__(self, other):
        return self._id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._id)

    @property
    def inspect(self):
        if not self._inspect:
            self._inspect = self._interface.inspect(self._id)
        return self._inspect

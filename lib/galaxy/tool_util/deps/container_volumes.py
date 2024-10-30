import shlex
from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import Optional


class ContainerVolume(metaclass=ABCMeta):
    valid_modes = frozenset({"ro", "rw", "z", "Z"})

    def __init__(self, path: str, host_path: Optional[str] = None, mode: Optional[str] = None):
        self.path = path
        self.host_path = host_path
        self.mode = mode
        if mode and not self.mode_is_valid:
            raise ValueError(f"Invalid container volume mode: {mode}")

    @abstractmethod
    def from_str(cls, as_str: str) -> "ContainerVolume":
        """Classmethod to convert from this container type's string representation.

        :param  as_str: string representation of volume
        :type   as_str: str
        """

    @abstractmethod
    def __str__(self) -> str:
        """Return this container type's string representation of the volume."""

    @property
    def mode_is_valid(self) -> bool:
        return self.mode in self.valid_modes


class DockerVolume(ContainerVolume):
    @classmethod
    def from_str(cls, as_str: str) -> "DockerVolume":
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
            if any(mode_part not in DockerVolume.valid_modes for mode_part in parts[1].split(",")):
                kwds["mode"] = parts[1]
                kwds["path"] = kwds["host_path"]
            else:
                kwds["path"] = parts[1]
        elif len(parts) == 3:
            kwds["path"] = parts[1]
            kwds["mode"] = parts[2]
        return cls(**kwds)

    def __str__(self) -> str:
        volume_str = ":".join(x for x in (self.host_path, self.path, self.mode) if x is not None)
        if "$" not in volume_str:
            volume_for_cmd_line = shlex.quote(volume_str)
        else:
            # e.g. $_GALAXY_JOB_TMP_DIR:$_GALAXY_JOB_TMP_DIR:rw so don't single quote.
            volume_for_cmd_line = f'"{volume_str}"'
        return volume_for_cmd_line

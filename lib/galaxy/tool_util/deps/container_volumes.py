"""Shadow galaxy.util.container_volumes for backward compatibility."""

from galaxy.util.container_volumes import (
    ContainerVolume,
    DockerVolume,
)

__all__ = (
    "ContainerVolume",
    "DockerVolume",
)

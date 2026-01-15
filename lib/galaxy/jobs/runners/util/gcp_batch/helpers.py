"""Helper functions and constants for GCP Batch runner."""

import logging
import re

log = logging.getLogger(__name__)

# Default values for GCP Batch runner configuration
DEFAULT_NFS_MOUNT_PATH = "/mnt/nfs"
DEFAULT_NFS_PATH = "/"
DEFAULT_MEMORY_MIB = 2048
DEFAULT_CPU_MILLI = 1000
DEFAULT_CVMFS_DOCKER_VOLUME = '-v "/cvmfs/data.galaxyproject.org:/cvmfs/data.galaxyproject.org:ro"'


def parse_volume_spec(volume_spec):
    """
    Parse a volume specification string into a volume dictionary.

    Format: "server:/remote_path:/mount_path[:r]"

    Examples:
        "10.0.0.1:/galaxy:/mnt/nfs"
        "nfs-server:/exports/data:/data:r"

    Returns a dict with keys:
        - server: NFS server hostname/IP
        - remote_path: path on NFS server
        - mount_path: local mount path
        - read_only: boolean

    Returns None if the specification is invalid.
    """
    if not volume_spec:
        return None

    # Split on colons, but we need to handle the structure carefully
    # Format: server:/remote_path:/mount_path[:r]
    parts = volume_spec.split(":")

    if len(parts) < 3:
        log.warning(
            "Invalid volume specification: %s (expected server:/remote_path:/mount_path[:r])",
            volume_spec,
        )
        return None

    server = parts[0].strip()
    remote_path = parts[1].strip()
    mount_path = parts[2].strip()
    read_only = len(parts) > 3 and parts[3].strip().lower() in ("ro", "r", "readonly")

    if not server or not remote_path or not mount_path:
        log.warning(
            "Invalid volume specification: %s (server, remote_path, and mount_path are required)",
            volume_spec,
        )
        return None

    return {
        "server": server,
        "remote_path": remote_path,
        "mount_path": mount_path,
        "read_only": read_only,
    }


def parse_volumes_param(volumes_param):
    """
    Parse the gcp_batch_volumes parameter (comma-separated volume specs).

    Example:
        "10.0.0.1:/galaxy:/mnt/nfs,cvmfs-proxy:/cvmfs:/cvmfs:ro"

    Returns a list of volume dictionaries.
    """
    if not volumes_param:
        return []

    volumes = []
    for spec in volumes_param.split(","):
        spec = spec.strip()
        if spec:
            vol = parse_volume_spec(spec)
            if vol:
                volumes.append(vol)
    return volumes


def parse_docker_volumes_param(docker_volumes_param):
    """
    Parse the docker_extra_volumes parameter for additional docker -v mounts.

    Example:
        "/cvmfs/data.galaxyproject.org:/cvmfs/data.galaxyproject.org:ro,/local/path:/container/path"

    Returns a string of docker -v arguments suitable for passing to docker run.
    """
    if not docker_volumes_param:
        return ""

    volume_args = []
    for spec in docker_volumes_param.split(","):
        spec = spec.strip()
        if spec:
            volume_args.append(f'-v "{spec}"')
    return " ".join(volume_args)


def convert_cpu_to_milli(cpu_str):
    """
    Convert CPU specification to milli-cores.
    Supports formats like: "1", "1.5", "500m", "0.5"
    """
    if not cpu_str:
        return DEFAULT_CPU_MILLI

    cpu_str = str(cpu_str).strip()

    # Handle milli-core format (e.g., "500m")
    if cpu_str.endswith("m"):
        try:
            return int(cpu_str[:-1])
        except ValueError:
            log.warning("Invalid CPU format: %s, using default", cpu_str)
            return DEFAULT_CPU_MILLI

    # Handle decimal format (e.g., "1.5", "0.5")
    try:
        cpu_float = float(cpu_str)
        return int(cpu_float * 1000)
    except ValueError:
        log.warning("Invalid CPU format: %s, using default", cpu_str)
        return DEFAULT_CPU_MILLI


def convert_memory_to_mib(memory_str):
    """
    Convert memory specification to MiB.
    Supports formats like: "1Gi", "512Mi", "1024M", "1G", "2048"
    """
    if not memory_str:
        return DEFAULT_MEMORY_MIB

    memory_str = str(memory_str).strip()

    # Handle plain numbers (assume MiB)
    if memory_str.isdigit():
        return int(memory_str)

    # Extract number and unit
    match = re.match(r"^(\d+(?:\.\d+)?)\s*([A-Za-z]*)$", memory_str)
    if not match:
        log.warning("Invalid memory format: %s, using default", memory_str)
        return DEFAULT_MEMORY_MIB

    value = float(match.group(1))
    unit = match.group(2).lower()

    # Convert to MiB based on unit
    if unit in ["", "mib", "mi"]:
        return int(value)
    elif unit in ["gib", "gi"]:
        return int(value * 1024)  # GiB to MiB
    elif unit in ["mb", "m"]:
        return int(value * 1000 / 1024)  # MB to MiB (decimal to binary)
    elif unit in ["gb", "g"]:
        return int(value * 1000 * 1000 / 1024 / 1024)  # GB to MiB
    elif unit in ["kib", "ki"]:
        return int(value / 1024)  # KiB to MiB
    elif unit in ["kb", "k"]:
        return int(value * 1000 / 1024 / 1024)  # KB to MiB
    else:
        log.warning("Unknown memory unit: %s, treating as MiB", unit)
        return int(value)


def sanitize_label_value(value, max_length=63):
    """Sanitize a value to be used as a GCP label value."""
    if not value:
        return "unknown"

    # Convert to lowercase and replace invalid characters with dashes
    sanitized = "".join(c.lower() if c.isalnum() else "-" for c in str(value))

    # Remove consecutive dashes
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")

    # Ensure it starts and ends with alphanumeric characters
    sanitized = sanitized.strip("-")
    if not sanitized:
        return "unknown"

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip("-")

    # Ensure it's not empty after truncation
    return sanitized if sanitized else "unknown"

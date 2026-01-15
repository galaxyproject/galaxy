"""Helper functions for GCP Batch runner."""

import logging
import re

log = logging.getLogger(__name__)


def convert_cpu_to_milli(cpu_str):
    """
    Convert CPU specification to milli-cores.
    Supports formats like: "1", "1.5", "500m", "0.5"
    """
    if not cpu_str:
        return 1000  # Default to 1 vCPU

    cpu_str = str(cpu_str).strip()

    # Handle milli-core format (e.g., "500m")
    if cpu_str.endswith("m"):
        try:
            return int(cpu_str[:-1])
        except ValueError:
            log.warning("Invalid CPU format: %s, using default", cpu_str)
            return 1000

    # Handle decimal format (e.g., "1.5", "0.5")
    try:
        cpu_float = float(cpu_str)
        return int(cpu_float * 1000)
    except ValueError:
        log.warning("Invalid CPU format: %s, using default", cpu_str)
        return 1000


def convert_memory_to_mib(memory_str):
    """
    Convert memory specification to MiB.
    Supports formats like: "1Gi", "512Mi", "1024M", "1G", "2048"
    """
    if not memory_str:
        return 2048  # Default to 2 GiB

    memory_str = str(memory_str).strip()

    # Handle plain numbers (assume MiB)
    if memory_str.isdigit():
        return int(memory_str)

    # Extract number and unit
    match = re.match(r"^(\d+(?:\.\d+)?)\s*([A-Za-z]*)$", memory_str)
    if not match:
        log.warning("Invalid memory format: %s, using default", memory_str)
        return 2048

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

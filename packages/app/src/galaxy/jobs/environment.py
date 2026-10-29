"""Typed shell setup entries used by destination configuration and job runners.

Destination environment entries are ordered job configuration, separate from the
runner parameters persisted on jobs. The ``type`` field controls forwarding into
wrapped tool containers; it does not change how a statement runs in the job script.
"""

from collections.abc import Mapping
from typing import (
    cast,
    Literal,
    TypeGuard,
)

from typing_extensions import (
    NotRequired,
    TypedDict,
)

from galaxy.tool_util_models.runtime_environment import validate_environment_variable_name

EnvironmentScope = Literal["job", "tool"]
"""A job statement stays outside wrapped containers; a tool entry forwards its name."""


class EnvironmentStatement(TypedDict, total=False):
    """A shell variable assignment, sourced file, or executed setup command.

    Existing callers may provide nullable fields. A sourced file takes precedence
    over an executed command, which takes precedence over a name/value assignment.
    """

    name: str | None
    """Variable to export when this entry is an assignment."""
    value: str | None
    """Assignment value; an empty string is distinct from an unset variable."""
    file: str | None
    """Path to a shell script to source in the job environment."""
    execute: str | None
    """Shell command to execute while setting up the job environment."""
    raw: bool
    """Use the value or file path as shell syntax instead of quoting it."""
    job_directory_path: str
    """Local file to stage when a tool's generated assignment reads that file."""


class JobEnvironmentEntry(EnvironmentStatement):
    """A destination entry available to host-side setup and non-containerized tools.

    Parsers always write ``type="job"``. Omitting it remains supported for legacy
    callers that construct or mutate ``JobDestination.env`` directly.
    """

    type: NotRequired[Literal["job"]]


class ToolEnvironmentEntry(TypedDict):
    """A variable exported in the job script and forwarded into a tool container.

    The name and value are required. Files and commands are deliberately excluded:
    Galaxy needs an explicit variable name to forward its final job environment value.
    """

    type: Literal["tool"]
    """Forward the named variable into a wrapped tool container."""
    name: str
    """Validated shell variable name, deduplicated when building forwarding options."""
    value: str
    """Value exported in the job script; later statements may override it."""
    raw: NotRequired[bool]
    """Treat the value as shell syntax, using the same rules as job assignments."""


DestinationEnvironmentEntry = JobEnvironmentEntry | ToolEnvironmentEntry
"""A serializable destination entry; list position defines shell statement order."""


def is_tool_environment_entry(entry: DestinationEnvironmentEntry) -> TypeGuard[ToolEnvironmentEntry]:
    """Narrow an entry to an explicitly forwarded name/value assignment."""
    return entry.get("type") == "tool"


def normalize_environment_entry(
    entry: Mapping[str, object], scope: EnvironmentScope | None = None
) -> DestinationEnvironmentEntry:
    """Copy an entry, normalize legacy scope, and validate tool-only assignments.

    An explicit scope comes from ``job_env`` or ``tool_env`` in configuration and
    overrides any incoming discriminator. Unscoped legacy ``env`` entries are job
    scoped; already normalized entries retain their type.
    """
    entry_type = scope if scope is not None else entry.get("type", "job")
    if entry_type not in ("job", "tool"):
        raise ValueError(f"Unknown destination environment entry type: {entry_type}")
    normalized = dict(entry)
    normalized["type"] = entry_type
    if entry_type == "job":
        return cast(JobEnvironmentEntry, normalized)

    if "file" in normalized or "execute" in normalized:
        raise ValueError("tool_env accepts only name/value entries (plus raw), not file/execute")
    name = normalized.get("name")
    value = normalized.get("value")
    if not isinstance(name, str) or not isinstance(value, str):
        raise ValueError("tool_env entries require a string name and value")
    if normalized.keys() - {"type", "name", "value", "raw"}:
        raise ValueError("tool_env accepts only name/value entries (plus raw)")
    if "raw" in normalized and not isinstance(normalized["raw"], bool):
        raise ValueError("tool_env raw must be a boolean")
    validate_environment_variable_name(name)
    return cast(ToolEnvironmentEntry, normalized)

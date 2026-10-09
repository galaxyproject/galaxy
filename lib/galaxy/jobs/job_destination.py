from dataclasses import (
    dataclass,
    field,
    InitVar,
)
from typing import (
    Any,
    TYPE_CHECKING,
    Union,
)

from .environment import (
    DestinationEnvironmentEntry,
    is_tool_environment_entry,
    normalize_environment_entry,
)

if TYPE_CHECKING:
    from galaxy.jobs import ResubmitConfigDict
    from galaxy.model import Job


@dataclass(kw_only=True, eq=False)
class JobDestination:
    """
    Provides details about where a job runs
    """

    id: str | None = None
    url: str | None = None
    tags: list[str] | None = None
    runner: str | None = None
    legacy: bool = False
    converted: bool = False
    shell: str | None = None
    env: list[DestinationEnvironmentEntry] = field(default_factory=list)
    """Ordered scoped statements, never included in persisted destination params."""
    resubmit: list["ResubmitConfigDict"] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    from_job: InitVar[Union["Job", None]] = None

    def __post_init__(self, from_job: Union["Job", None] = None) -> None:
        self.env = [normalize_environment_entry(entry) for entry in self.env]
        # Use the values persisted in an existing job
        if from_job is not None and from_job.destination_id is not None:
            self.id = from_job.destination_id
            self.params = from_job.destination_params or {}

    @property
    def tool_env_names(self) -> list[str]:
        return list(dict.fromkeys(entry["name"] for entry in self.env if is_tool_environment_entry(entry)))

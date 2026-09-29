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

from galaxy.tool_util_models.runtime_environment import validate_environment_variable_name

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
    env: list[dict[str, Any]] = field(default_factory=list)
    job_env: list[dict[str, Any]] = field(default_factory=list)
    tool_env: list[dict[str, Any]] = field(default_factory=list)
    env_order: list[tuple[str, int]] = field(default_factory=list)
    resubmit: list["ResubmitConfigDict"] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    from_job: InitVar[Union["Job", None]] = None

    def __post_init__(self, from_job: Union["Job", None] = None) -> None:
        for entry in self.tool_env:
            if "file" in entry or "execute" in entry:
                raise ValueError("tool_env accepts only name/value entries (plus raw), not file/execute")
            if not entry.get("name") or "value" not in entry:
                raise ValueError("tool_env entries require name and value")
            if any(key not in {"name", "value", "raw"} for key in entry):
                raise ValueError("tool_env accepts only name/value entries (plus raw)")
            validate_environment_variable_name(entry["name"])
        # Use the values persisted in an existing job
        if from_job is not None and from_job.destination_id is not None:
            self.id = from_job.destination_id
            self.params = from_job.destination_params or {}

    @property
    def environment(self) -> list[dict[str, Any]]:
        """Export entries in configuration order, including dynamically appended entries."""
        if self.env_order:
            ordered = [
                getattr(self, scope)[index] for scope, index in self.env_order if index < len(getattr(self, scope))
            ]
            seen = set(self.env_order)
            ordered.extend(
                entry
                for scope in ("env", "job_env", "tool_env")
                for index, entry in enumerate(getattr(self, scope))
                if (scope, index) not in seen
            )
            return ordered
        return [*self.env, *self.job_env, *self.tool_env]

    @property
    def tool_env_names(self) -> list[str]:
        return list(dict.fromkeys(entry["name"] for entry in self.tool_env))

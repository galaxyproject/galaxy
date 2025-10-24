import sys
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

if TYPE_CHECKING:
    from galaxy.jobs import ResubmitConfigDict
    from galaxy.model import Job

dataclass_kwargs = {"kw_only": True} if sys.version_info >= (3, 10) else {}


@dataclass(**dataclass_kwargs, eq=False)
class JobDestination:
    """
    Provides details about where a job runs
    """

    id: Union[str, None] = None
    url: Union[str, None] = None
    tags: Union[list[str], None] = None
    runner: Union[str, None] = None
    legacy: bool = False
    converted: bool = False
    shell: Union[str, None] = None
    env: list[dict[str, Any]] = field(default_factory=list)
    resubmit: list["ResubmitConfigDict"] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    from_job: InitVar[Union["Job", None]] = None

    def __post_init__(self, from_job: Union["Job", None] = None) -> None:
        # Use the values persisted in an existing job
        if from_job is not None and from_job.destination_id is not None:
            self.id = from_job.destination_id
            self.params = from_job.destination_params or {}

"""The job metrics plugin that records Galaxy-level resubmissions."""

from typing import (
    Any,
    TYPE_CHECKING,
)

from sqlalchemy import (
    func,
    select,
)

from galaxy import model
from . import InstrumentPlugin
from ..formatting import (
    FormattedMetric,
    JobMetricFormatter,
)
from ..safety import Safety

if TYPE_CHECKING:
    from galaxy.app import GalaxyManagerApplication

RESUBMISSION_COUNT_KEY = "resubmission_count"


class ResubmissionPluginFormatter(JobMetricFormatter):
    def format(self, key: str, value: Any) -> FormattedMetric:
        return FormattedMetric("Resubmission Count", str(int(value)))


class ResubmissionPlugin(InstrumentPlugin):
    """Count Galaxy-visible job resubmission events from persisted state history."""

    plugin_type = "resubmission"
    formatter = ResubmissionPluginFormatter()
    default_safety = Safety.SAFE

    def __init__(self, app: "GalaxyManagerApplication | None" = None, **kwargs):
        self.app = app

    def job_properties(self, job_id: int, job_directory: str) -> dict[str, int]:
        if self.app is None:
            return {}

        statement = (
            select(func.count())
            .select_from(model.JobStateHistory)
            .where(
                model.JobStateHistory.job_id == job_id,
                model.JobStateHistory.state == model.Job.states.RESUBMITTED,
            )
        )
        count = self.app.model.context.scalar(statement)
        return {RESUBMISSION_COUNT_KEY: int(count or 0)}


__all__ = ("ResubmissionPlugin",)

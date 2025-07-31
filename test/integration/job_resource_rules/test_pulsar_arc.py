"""Dynamic job rule for the Pulsar ARC (Advanced Resource Connector) job runner integration tests.

This file contains a dynamic job rule for the Pulsar ARC job runner integration tests in
`test/integration/test_pulsar_arc.py`. The rule allows selecting a job destination based on a dynamic reference that can
be read and updated during the tests using `test_pulsar_arc_get_job_destination()` and
`test_pulsar_arc_set_job_destination()` respectively.
"""

from typing import Optional

from galaxy.app import UniverseApplication
from galaxy.jobs import JobMappingException  # type: ignore[attr-defined]
from galaxy.jobs import (
    JobDestination,
)
from galaxy.model import (
    Job,
    User as GalaxyUser,
)
from galaxy.tools import Tool as GalaxyTool

__all__ = ("test_pulsar_arc", "test_pulsar_arc_get_job_destination", "test_pulsar_arc_set_job_destination")


test_pulsar_arc_job_destination_ref: list[JobDestination] = []


def test_pulsar_arc_get_job_destination() -> Optional[JobDestination]:
    """
    Return the last stored job destination (if any).
    """
    return test_pulsar_arc_job_destination_ref[0] if test_pulsar_arc_job_destination_ref else None


def test_pulsar_arc_set_job_destination(job_destination: JobDestination) -> None:
    """
    Store a job destination, overwriting any previous one.
    """
    test_pulsar_arc_job_destination_ref[:] = [job_destination]


def test_pulsar_arc(app: UniverseApplication, job: Job, tool: GalaxyTool, user: GalaxyUser) -> JobDestination:
    """
    Dynamic job rule that maps jobs to the stored job destination.
    """
    job_destination = test_pulsar_arc_get_job_destination()
    if not job_destination:
        raise JobMappingException("No job destination set for dynamic job rule.")

    return job_destination

from fastapi import Body

from galaxy.managers.jobs import (
    JobLock,
    JobManager,
)
from . import (
    depends,
    Router,
)

router = Router(tags=["job_lock"])


@router.get("/api/job_lock", require_admin=True)
def job_lock_status(job_manager: JobManager = depends(JobManager)) -> JobLock:
    """Get job lock status."""
    return job_manager.job_lock()


@router.put("/api/job_lock", require_admin=True)
def update_job_lock(job_manager: JobManager = depends(JobManager), job_lock: JobLock = Body(...)) -> JobLock:
    """Set job lock status."""
    return job_manager.update_job_lock(job_lock)

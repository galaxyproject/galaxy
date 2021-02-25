from fastapi import (
    Body,
)
from fastapi_utils.inferring_router import InferringRouter as APIRouter

from galaxy.managers.jobs import JobLock, JobManager
from . import AdminUserRequired, depends

router = APIRouter(tags=['job_lock'])


@router.get('/api/job_lock', dependencies=[AdminUserRequired])
def job_lock_status(job_manager: JobManager = depends(JobManager)) -> JobLock:
    """Get job lock status."""
    return job_manager.job_lock()


@router.put('/api/job_lock', dependencies=[AdminUserRequired])
def update_job_lock(job_manager: JobManager = depends(JobManager), job_lock: JobLock = Body(...)) -> JobLock:
    """Set job lock status."""
    return job_manager.update_job_lock(job_lock)

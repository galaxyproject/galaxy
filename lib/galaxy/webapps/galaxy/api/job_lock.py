from fastapi import (
    Body,
    Depends,
)
from fastapi_utils.inferring_router import InferringRouter as APIRouter

from galaxy.managers.jobs import JobLock
from . import get_admin_user, get_job_manager

router = APIRouter(tags=['job_lock'])


@router.get('/api/job_lock')
def job_lock_status(job_manager=Depends(get_job_manager), admin_user=Depends(get_admin_user)) -> JobLock:
    """Get job lock status."""
    return job_manager.job_lock()


@router.put('/api/job_lock')
def update_job_lock(job_manager=Depends(get_job_manager), admin_user=Depends(get_admin_user), job_lock: JobLock = Body(...)) -> JobLock:
    """Set job lock status."""
    return job_manager.update_job_lock(job_lock)

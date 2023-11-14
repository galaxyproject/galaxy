from enum import Enum
from typing import (
    Any,
    Dict,
    Optional,
)

from galaxy import (
    exceptions,
    model,
)
from galaxy.managers import hdas
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.jobs import (
    JobManager,
    JobSearch,
    view_show_job,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import JobIndexQueryPayload


class JobIndexViewEnum(str, Enum):
    collection = "collection"
    admin_job_list = "admin_job_list"


class JobIndexPayload(JobIndexQueryPayload):
    view: JobIndexViewEnum = JobIndexViewEnum.collection


class JobsService:
    job_manager: JobManager
    job_search: JobSearch
    hda_manager: hdas.HDAManager

    def __init__(
        self,
        job_manager: JobManager,
        job_search: JobSearch,
        hda_manager: hdas.HDAManager,
    ):
        self.job_manager = job_manager
        self.job_search = job_search
        self.hda_manager = hda_manager

    def show(
        self,
        trans: ProvidesUserContext,
        id: DecodedDatabaseIdField,
        full: bool = False,
    ) -> Dict[str, Any]:
        job = self.job_manager.get_accessible_job(trans, id)
        return view_show_job(trans, job, bool(full))

    def index(
        self,
        trans: ProvidesUserContext,
        payload: JobIndexPayload,
    ):
        security = trans.security
        is_admin = trans.user_is_admin
        view = payload.view
        if view == JobIndexViewEnum.admin_job_list:
            payload.user_details = True
        user_details = payload.user_details
        decoded_user_id = payload.user_id

        if not is_admin:
            self._check_nonadmin_access(view, user_details, decoded_user_id, trans.user.id)

        jobs = self.job_manager.index_query(trans, payload)
        out = []
        for job in jobs.yield_per(model.YIELD_PER_ROWS):
            job_dict = job.to_dict(view, system_details=is_admin)
            j = security.encode_all_ids(job_dict, True)
            if view == JobIndexViewEnum.admin_job_list:
                j["decoded_job_id"] = job.id
            if user_details:
                j["user_email"] = job.get_user_email()
            out.append(j)

        return out

    def _check_nonadmin_access(
        self, view: str, user_details: bool, decoded_user_id: Optional[DecodedDatabaseIdField], trans_user_id: int
    ):
        """Verify admin-only resources are not being accessed."""
        if view == JobIndexViewEnum.admin_job_list:
            raise exceptions.AdminRequiredException("Only admins can use the admin_job_list view")
        if user_details:
            raise exceptions.AdminRequiredException("Only admins can index the jobs with user details enabled")
        if decoded_user_id is not None and decoded_user_id != trans_user_id:
            raise exceptions.AdminRequiredException("Only admins can index the jobs of others")

from enum import Enum
from typing import (
    Any,
    Dict,
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
        if payload.view == JobIndexViewEnum.admin_job_list:
            payload.user_details = True
        user_details = payload.user_details
        if payload.view == JobIndexViewEnum.admin_job_list and not is_admin:
            raise exceptions.AdminRequiredException("Only admins can use the admin_job_list view")
        query = self.job_manager.index_query(trans, payload)
        out = []
        view = payload.view
        for job in query.yield_per(model.YIELD_PER_ROWS):
            job_dict = job.to_dict(view, system_details=is_admin)
            j = security.encode_all_ids(job_dict, True)
            if view == JobIndexViewEnum.admin_job_list:
                j["decoded_job_id"] = job.id
            if user_details:
                j["user_email"] = job.get_user_email()
            out.append(j)

        return out

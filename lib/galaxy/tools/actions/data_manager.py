import logging
from typing import Optional

from galaxy.model import (
    History,
    Job,
)
from galaxy.model.base import transaction
from galaxy.model.dataset_collections.matching import MatchingCollections
from galaxy.tools._types import ToolStateJobInstancePopulatedT
from galaxy.tools.execute import (
    DatasetCollectionElementsSliceT,
    DEFAULT_DATASET_COLLECTION_ELEMENTS,
    DEFAULT_JOB_CALLBACK,
    DEFAULT_PREFERRED_OBJECT_STORE_ID,
    DEFAULT_RERUN_REMAP_JOB_ID,
    DEFAULT_SET_OUTPUT_HID,
    JobCallbackT,
)
from galaxy.tools.execution_helpers import ToolExecutionCache
from . import (
    DefaultToolAction,
    ToolActionExecuteResult,
)

log = logging.getLogger(__name__)


class DataManagerToolAction(DefaultToolAction):
    """Tool action used for Data Manager Tools"""

    def execute(
        self,
        tool,
        trans,
        incoming: Optional[ToolStateJobInstancePopulatedT] = None,
        history: Optional[History] = None,
        job_params=None,
        rerun_remap_job_id: Optional[int] = DEFAULT_RERUN_REMAP_JOB_ID,
        execution_cache: Optional[ToolExecutionCache] = None,
        dataset_collection_elements: Optional[DatasetCollectionElementsSliceT] = DEFAULT_DATASET_COLLECTION_ELEMENTS,
        completed_job: Optional[Job] = None,
        collection_info: Optional[MatchingCollections] = None,
        job_callback: Optional[JobCallbackT] = DEFAULT_JOB_CALLBACK,
        preferred_object_store_id: Optional[str] = DEFAULT_PREFERRED_OBJECT_STORE_ID,
        set_output_hid: bool = DEFAULT_SET_OUTPUT_HID,
        flush_job: bool = True,
        skip: bool = False,
    ) -> ToolActionExecuteResult:
        rval = super().execute(
            tool,
            trans,
            incoming=incoming,
            history=history,
            job_params=job_params,
            rerun_remap_job_id=rerun_remap_job_id,
            execution_cache=execution_cache,
            dataset_collection_elements=dataset_collection_elements,
            completed_job=completed_job,
            collection_info=collection_info,
            job_callback=job_callback,
            preferred_object_store_id=preferred_object_store_id,
            set_output_hid=set_output_hid,
            flush_job=flush_job,
            skip=skip,
        )
        if isinstance(rval, tuple) and len(rval) >= 2 and isinstance(rval[0], trans.app.model.Job):
            assoc = trans.app.model.DataManagerJobAssociation(job=rval[0], data_manager_id=tool.data_manager_id)
            trans.sa_session.add(assoc)
            with transaction(trans.sa_session):
                trans.sa_session.commit()
        else:
            log.error(f"Got bad return value from DefaultToolAction.execute(): {rval}")
        return rval

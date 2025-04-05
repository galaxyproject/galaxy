import logging
from typing import (
    Optional,
    TYPE_CHECKING,
)

from galaxy.model import (
    History,
    Job,
)
from galaxy.model.dataset_collections.matching import MatchingCollections
from galaxy.objectstore import ObjectStorePopulator
from galaxy.tools._types import ToolStateJobInstancePopulatedT
from galaxy.tools.actions import (
    DefaultToolAction,
    OutputCollections,
    OutputDatasetsT,
    ToolActionExecuteResult,
)
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

if TYPE_CHECKING:
    from galaxy.managers.context import ProvidesUserContext
    from galaxy.tools import (
        DatabaseOperationTool,
        Tool,
    )

log = logging.getLogger(__name__)


class ModelOperationToolAction(DefaultToolAction):
    produces_real_jobs: bool = False

    def check_inputs_ready(self, tool, trans, incoming, history, execution_cache=None, collection_info=None):
        if execution_cache is None:
            execution_cache = ToolExecutionCache(trans)

        current_user_roles = execution_cache.current_user_roles
        history, inp_data, inp_dataset_collections, _, _, _ = self._collect_inputs(
            tool, trans, incoming, history, current_user_roles, collection_info
        )

        tool.check_inputs_ready(inp_data, inp_dataset_collections, security=trans.security)

    def execute(
        self,
        tool: "Tool",
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
        from galaxy.tools import DatabaseOperationTool

        assert isinstance(tool, DatabaseOperationTool)
        incoming = incoming or {}
        trans.check_user_activation()

        if execution_cache is None:
            execution_cache = ToolExecutionCache(trans)

        current_user_roles = execution_cache.current_user_roles
        (
            history,
            inp_data,
            inp_dataset_collections,
            preserved_tags,
            preserved_hdca_tags,
            all_permissions,
        ) = self._collect_inputs(tool, trans, incoming, history, current_user_roles, collection_info)

        # Build name for output datasets based on tool name and input names
        on_text = self._get_on_text(inp_data)

        # wrapped params are used by change_format action and by output.label; only perform this wrapping once, as needed
        wrapped_params = self._wrapped_params(trans, tool, incoming)

        out_data: OutputDatasetsT = {}
        input_collections = {k: v[0][0] for k, v in inp_dataset_collections.items()}
        output_collections = OutputCollections(
            trans,
            history,
            tool=tool,
            tool_action=self,
            input_collections=input_collections,
            dataset_collection_elements=dataset_collection_elements,
            on_text=on_text,
            incoming=incoming,
            params=wrapped_params.params,
            job_params=job_params,
            tags=preserved_tags,
            hdca_tags=preserved_hdca_tags,
        )

        #
        # Create job.
        #
        job, galaxy_session = self._new_job_for_session(trans, tool, history)
        self._produce_outputs(
            trans,
            tool,
            out_data,
            output_collections,
            incoming=incoming,
            history=history,
            tags=preserved_tags,
            hdca_tags=preserved_hdca_tags,
            skip=skip,
        )
        self._record_inputs(trans, tool, job, incoming, inp_data, inp_dataset_collections)
        self._record_outputs(job, out_data, output_collections)
        if job_callback:
            job_callback(job)
        if skip:
            job.state = job.states.SKIPPED
        else:
            job.state = job.states.OK
        trans.sa_session.add(job)

        # Queue the job for execution
        # trans.app.job_manager.job_queue.put( job.id, tool.id )
        # trans.log_event( "Added database job action to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )
        log.info(f"Calling produce_outputs, tool is {tool}")
        return job, out_data, history

    def _produce_outputs(
        self,
        trans: "ProvidesUserContext",
        tool: "DatabaseOperationTool",
        out_data,
        output_collections,
        incoming,
        history,
        tags,
        hdca_tags,
        skip,
    ):
        tool.produce_outputs(
            trans,
            out_data,
            output_collections,
            incoming,
            history=history,
            tags=tags,
            hdca_tags=hdca_tags,
        )
        if mapped_over_elements := output_collections.dataset_collection_elements:
            for name, value in out_data.items():
                if name in mapped_over_elements:
                    value.visible = False
                    mapped_over_elements[name].hda = value

        # We probably need to mark all outputs as skipped, not just the outputs of whatever the database op tools do ?
        # This is probably not exactly right, but it might also work in most cases
        if skip:
            for output_collection in output_collections.out_collections.values():
                output_collection.mark_as_populated()
            object_store_populator = ObjectStorePopulator(trans.app, trans.user)
            for hdca in output_collections.out_collection_instances.values():
                hdca.visible = False
                # Would we also need to replace the datasets with skipped datasets?
                for data in hdca.dataset_instances:
                    data.set_skipped(object_store_populator)
        trans.sa_session.add_all(out_data.values())

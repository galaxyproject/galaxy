import logging
from collections import OrderedDict

from galaxy.tools.actions import (
    DefaultToolAction,
    OutputCollections,
    ToolExecutionCache,
)

log = logging.getLogger(__name__)


class ModelOperationToolAction(DefaultToolAction):
    produces_real_jobs = False

    def check_inputs_ready(self, tool, trans, incoming, history, execution_cache=None, collection_info=None):
        if execution_cache is None:
            execution_cache = ToolExecutionCache(trans)

        current_user_roles = execution_cache.current_user_roles
        history, inp_data, inp_dataset_collections, _, _ = self._collect_inputs(tool, trans, incoming, history, current_user_roles, collection_info)

        tool.check_inputs_ready(inp_data, inp_dataset_collections)

    def execute(self, tool, trans, incoming={}, set_output_hid=False, overwrite=True, history=None, job_params=None, execution_cache=None, collection_info=None, **kwargs):
        trans.check_user_activation()

        if execution_cache is None:
            execution_cache = ToolExecutionCache(trans)

        current_user_roles = execution_cache.current_user_roles
        history, inp_data, inp_dataset_collections, preserved_tags, all_permissions = self._collect_inputs(tool, trans, incoming, history, current_user_roles, collection_info)

        # Build name for output datasets based on tool name and input names
        on_text = self._get_on_text(inp_data)

        # wrapped params are used by change_format action and by output.label; only perform this wrapping once, as needed
        wrapped_params = self._wrapped_params(trans, tool, incoming)

        out_data = OrderedDict()
        input_collections = dict((k, v[0][0]) for k, v in inp_dataset_collections.items())
        output_collections = OutputCollections(
            trans,
            history,
            tool=tool,
            tool_action=self,
            input_collections=input_collections,
            dataset_collection_elements=kwargs.get("dataset_collection_elements", None),
            on_text=on_text,
            incoming=incoming,
            params=wrapped_params.params,
            job_params=job_params,
            tags=preserved_tags,
        )

        #
        # Create job.
        #
        job, galaxy_session = self._new_job_for_session(trans, tool, history)
        self._produce_outputs(trans, tool, out_data, output_collections, incoming=incoming, history=history, tags=preserved_tags)
        self._record_inputs(trans, tool, job, incoming, inp_data, inp_dataset_collections)
        self._record_outputs(job, out_data, output_collections)
        job.state = job.states.OK
        trans.sa_session.add(job)
        trans.sa_session.flush()  # ensure job.id are available

        # Queue the job for execution
        # trans.app.job_manager.job_queue.put( job.id, tool.id )
        # trans.log_event( "Added database job action to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )
        log.info("Calling produce_outputs, tool is %s" % tool)
        return job, out_data

    def _produce_outputs(self, trans, tool, out_data, output_collections, incoming, history, tags):
        tool.produce_outputs(trans, out_data, output_collections, incoming, history=history, tags=tags)
        mapped_over_elements = output_collections.dataset_collection_elements
        if mapped_over_elements:
            for name, value in out_data.items():
                if name in mapped_over_elements:
                    value.visible = False
                    mapped_over_elements[name].hda = value

        trans.sa_session.add_all(out_data.values())
        trans.sa_session.flush()

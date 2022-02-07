import logging
import os
from json import dumps

from galaxy.job_execution.datasets import DatasetPath
from galaxy.metadata import get_metadata_compute_strategy
from galaxy.util import asbool
from . import ToolAction

log = logging.getLogger(__name__)


class SetMetadataToolAction(ToolAction):
    """Tool action used for setting external metadata on an existing dataset"""

    produces_real_jobs = False

    def execute(
        self, tool, trans, incoming=None, set_output_hid=False, overwrite=True, history=None, job_params=None, **kwargs
    ):
        """
        Execute using a web transaction.
        """
        trans.check_user_activation()
        session = trans.get_galaxy_session()
        session_id = session and session.id
        history_id = trans.history and trans.history.id
        incoming = incoming or {}
        job, odict = self.execute_via_app(
            tool,
            trans.app,
            session_id,
            history_id,
            trans.user,
            incoming,
            set_output_hid,
            overwrite,
            history,
            job_params,
        )
        # FIXME: can remove this when logging in execute_via_app method.
        trans.log_event(f"Added set external metadata job to the job queue, id: {str(job.id)}", tool_id=job.tool_id)
        return job, odict

    def execute_via_app(
        self,
        tool,
        app,
        session_id,
        history_id,
        user=None,
        incoming=None,
        set_output_hid=False,
        overwrite=True,
        history=None,
        job_params=None,
    ):
        """
        Execute using application.
        """
        incoming = incoming or {}
        for name, value in incoming.items():
            # Why are we looping here and not just using a fixed input name? Needed?
            if not name.startswith("input"):
                continue
            if isinstance(value, app.model.HistoryDatasetAssociation):
                dataset = value
                dataset_name = name
                type = "hda"
                break
            elif isinstance(value, app.model.LibraryDatasetDatasetAssociation):
                dataset = value
                dataset_name = name
                type = "ldda"
                break
            else:
                raise Exception("The dataset to set metadata on could not be determined.")

        sa_session = app.model.context

        # Create the job object
        job = app.model.Job()
        job.galaxy_version = app.config.version_major
        job.session_id = session_id
        job.history_id = history_id
        job.tool_id = tool.id
        if user:
            job.user_id = user.id
        if job_params:
            job.params = dumps(job_params)
        start_job_state = job.state  # should be job.states.NEW
        try:
            # For backward compatibility, some tools may not have versions yet.
            job.tool_version = tool.version
        except AttributeError:
            job.tool_version = "1.0.1"
        job.dynamic_tool = tool.dynamic_tool
        job.state = (
            job.states.WAITING
        )  # we need to set job state to something other than NEW, or else when tracking jobs in db it will be picked up before we have added input / output parameters
        sa_session.add(job)
        sa_session.flush()  # ensure job.id is available

        # add parameters to job_parameter table
        # Store original dataset state, so we can restore it. A separate table might be better (no chance of 'losing' the original state)?
        incoming["__ORIGINAL_DATASET_STATE__"] = dataset.state
        input_paths = [DatasetPath(dataset.id, real_path=dataset.file_name, mutable=False)]
        app.object_store.create(job, base_dir="job_work", dir_only=True, extra_dir=str(job.id))
        job_working_dir = app.object_store.get_filename(job, base_dir="job_work", dir_only=True, extra_dir=str(job.id))
        datatypes_config = os.path.join(job_working_dir, "registry.xml")
        app.datatypes_registry.to_xml_file(path=datatypes_config)
        external_metadata_wrapper = get_metadata_compute_strategy(app.config, job.id, tool_id=tool.id)
        output_datatasets_dict = {
            dataset_name: dataset,
        }
        validate_outputs = asbool(incoming.get("validate", False))
        cmd_line = external_metadata_wrapper.setup_external_metadata(
            output_datatasets_dict,
            {},
            sa_session,
            exec_dir=None,
            tmp_dir=job_working_dir,
            dataset_files_path=app.model.Dataset.file_path,
            output_fnames=input_paths,
            config_root=app.config.root,
            config_file=app.config.config_file,
            datatypes_config=datatypes_config,
            job_metadata=os.path.join(job_working_dir, "working", tool.provided_metadata_file),
            include_command=False,
            max_metadata_value_size=app.config.max_metadata_value_size,
            max_discovered_files=app.config.max_discovered_files,
            validate_outputs=validate_outputs,
            job=job,
            kwds={"overwrite": overwrite},
        )
        incoming["__SET_EXTERNAL_METADATA_COMMAND_LINE__"] = cmd_line
        for name, value in tool.params_to_strings(incoming, app).items():
            job.add_parameter(name, value)
        # add the dataset to job_to_input_dataset table
        if type == "hda":
            job.add_input_dataset(dataset_name, dataset)
        elif type == "ldda":
            job.add_input_library_dataset(dataset_name, dataset)
        # Need a special state here to show that metadata is being set and also allow the job to run
        # i.e. if state was set to 'running' the set metadata job would never run, as it would wait for input (the dataset to set metadata on) to be in a ready state
        dataset._state = dataset.states.SETTING_METADATA
        job.state = start_job_state  # job inputs have been configured, restore initial job state
        sa_session.flush()

        # clear e.g. converted files
        dataset.datatype.before_setting_metadata(dataset)

        return job, {}

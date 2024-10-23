""" This module contains functionality to aid in extracting workflows from
histories.
"""

import logging
from typing import Optional

from galaxy import (
    exceptions,
    model,
)
from galaxy.model.base import (
    ensure_object_added_to_session,
    transaction,
)
from galaxy.tool_util.parser import ToolOutputCollectionPart
from galaxy.tools.parameters.basic import (
    DataCollectionToolParameter,
    DataToolParameter,
)
from galaxy.tools.parameters.grouping import (
    Conditional,
    Repeat,
    Section,
)
from galaxy.util import listify
from .steps import (
    attach_ordered_steps,
    order_workflow_steps_with_levels,
)

log = logging.getLogger(__name__)

WARNING_SOME_DATASETS_NOT_READY = "Some datasets still queued or running were ignored"


def extract_workflow(
    trans,
    user,
    history=None,
    job_ids=None,
    dataset_ids=None,
    dataset_collection_ids=None,
    workflow_name=None,
    dataset_names=None,
    dataset_collection_names=None,
):
    steps = extract_steps(
        trans,
        history=history,
        job_ids=job_ids,
        dataset_ids=dataset_ids,
        dataset_collection_ids=dataset_collection_ids,
        dataset_names=dataset_names,
        dataset_collection_names=None,
    )
    # Workflow to populate
    workflow = model.Workflow()
    workflow.name = workflow_name
    workflow.steps = steps
    # Order the steps if possible
    attach_ordered_steps(workflow)
    # And let's try to set up some reasonable locations on the canvas
    # (these are pretty arbitrary values)
    levorder = order_workflow_steps_with_levels(steps)
    base_pos = 10
    for i, steps_at_level in enumerate(levorder):
        for j, index in enumerate(steps_at_level):
            step = steps[index]
            step.position = dict(top=(base_pos + 120 * j), left=(base_pos + 220 * i))
    # Store it
    stored = model.StoredWorkflow()
    stored.user = user
    stored.name = workflow_name
    workflow.stored_workflow = stored
    stored.latest_workflow = workflow
    trans.sa_session.add(stored)
    ensure_object_added_to_session(workflow, session=trans.sa_session)
    with transaction(trans.sa_session):
        trans.sa_session.commit()
    return stored


def extract_steps(
    trans,
    history=None,
    job_ids=None,
    dataset_ids=None,
    dataset_collection_ids=None,
    dataset_names=None,
    dataset_collection_names=None,
):
    # Ensure job_ids and dataset_ids are lists (possibly empty)
    job_ids = listify(job_ids)
    dataset_ids = listify(dataset_ids)
    dataset_collection_ids = listify(dataset_collection_ids)
    # Convert both sets of ids to integers
    job_ids = [int(_) for _ in job_ids]
    dataset_ids = [int(_) for _ in dataset_ids]
    dataset_collection_ids = [int(_) for _ in dataset_collection_ids]
    # Find each job, for security we (implicitly) check that they are
    # associated with a job in the current history.
    summary = WorkflowSummary(trans, history)
    jobs = summary.jobs
    steps = []
    step_labels = set()
    hid_to_output_pair = {}
    # Input dataset steps
    for i, hid in enumerate(dataset_ids):
        step = model.WorkflowStep()
        step.type = "data_input"
        if dataset_names:
            name = dataset_names[i]
        else:
            name = "Input Dataset"
        if name not in step_labels:
            step.label = name
            step_labels.add(name)
        step.tool_inputs = dict(name=name)
        hid_to_output_pair[hid] = (step, "output")
        steps.append(step)
    for i, hid in enumerate(dataset_collection_ids):
        step = model.WorkflowStep()
        step.type = "data_collection_input"
        if hid not in summary.collection_types:
            raise exceptions.RequestParameterInvalidException(f"hid {hid} does not appear to be a collection")
        collection_type = summary.collection_types[hid]
        if dataset_collection_names:
            name = dataset_collection_names[i]
        else:
            name = "Input Dataset Collection"
        if name not in step_labels:
            step.label = name
            step_labels.add(name)
        step.tool_inputs = dict(name=name, collection_type=collection_type)
        hid_to_output_pair[hid] = (step, "output")
        steps.append(step)
    # Tool steps
    for job_id in job_ids:
        if job_id not in summary.job_id2representative_job:
            log.warning(f"job_id {job_id} not found in job_id2representative_job {summary.job_id2representative_job}")
            raise AssertionError("Attempt to create workflow with job not connected to current history")
        job = summary.job_id2representative_job[job_id]
        tool_inputs, associations = step_inputs(trans, job)
        step = model.WorkflowStep()
        step.type = "tool"
        step.tool_id = job.tool_id
        step.tool_version = job.tool_version
        step.tool_inputs = tool_inputs
        # NOTE: We shouldn't need to do two passes here since only
        #       an earlier job can be used as an input to a later
        #       job.
        for other_hid, input_name in associations:
            if job in summary.implicit_map_jobs:
                an_implicit_output_collection = jobs[job][0][1]
                input_collection = an_implicit_output_collection.find_implicit_input_collection(input_name)
                if input_collection:
                    other_hid = input_collection.hid
                else:
                    log.info(f"Cannot find implicit input collection for {input_name}")
            if other_hid in hid_to_output_pair:
                step_input = step.get_or_add_input(input_name)
                other_step, other_name = hid_to_output_pair[other_hid]
                conn = model.WorkflowStepConnection()
                conn.input_step_input = step_input
                # Should always be connected to an earlier step
                conn.output_step = other_step
                conn.output_name = other_name
        steps.append(step)
        # Store created dataset hids
        for assoc in job.output_datasets + job.output_dataset_collection_instances:
            assoc_name = assoc.name
            if ToolOutputCollectionPart.is_named_collection_part_name(assoc_name):
                continue
            if assoc_name.startswith("__new_primary_file"):
                continue
            if job in summary.implicit_map_jobs:
                hid = None
                for implicit_pair in jobs[job]:
                    query_assoc_name, dataset_collection = implicit_pair
                    if query_assoc_name == assoc_name or assoc_name.startswith(
                        f"__new_primary_file_{query_assoc_name}|"
                    ):
                        hid = summary.hid(dataset_collection)
                if hid is None:
                    template = (
                        "Failed to find matching implicit job - job id is %s, implicit pairs are %s, assoc_name is %s."
                    )
                    message = template % (job.id, jobs[job], assoc_name)
                    log.warning(message)
                    raise Exception("Failed to extract job.")
            else:
                if hasattr(assoc, "dataset"):
                    has_hid = assoc.dataset
                else:
                    has_hid = assoc.dataset_collection_instance
                hid = summary.hid(has_hid)
            if hid in hid_to_output_pair:
                log.warning(f"duplicate hid found in extract_steps [{hid}]")
            hid_to_output_pair[hid] = (step, assoc.name)
    return steps


class FakeJob:
    """
    Fake job object for datasets that have no creating_job_associations,
    they will be treated as "input" datasets.
    """

    def __init__(self, dataset):
        self.is_fake = True
        self.id = f"fake_{dataset.id}"
        self.name = self._guess_name_from_dataset(dataset)

    def _guess_name_from_dataset(self, dataset) -> Optional[str]:
        """Tries to guess the name of the fake job from the dataset associations."""
        if dataset.copied_from_history_dataset_association:
            return "Import from History"
        if dataset.copied_from_library_dataset_dataset_association:
            return "Import from Library"
        return None


class DatasetCollectionCreationJob:
    def __init__(self, dataset_collection):
        self.is_fake = True
        self.id = f"fake_{dataset_collection.id}"
        self.from_jobs = None
        self.name = "Dataset Collection Creation"
        self.disabled_why = "Dataset collection created in a way not compatible with workflows"

    def set_jobs(self, jobs):
        assert jobs is not None
        self.from_jobs = jobs


def summarize(trans, history=None):
    """Return mapping of job description to datasets for active items in
    supplied history - needed for building workflow from a history.

    Formerly call get_job_dict in workflow web controller.
    """
    summary = WorkflowSummary(trans, history)
    return summary.jobs, summary.warnings


class WorkflowSummary:
    def __init__(self, trans, history):
        if not history:
            history = trans.get_history()
        self.history = history
        self.warnings = set()
        self.jobs = {}
        self.job_id2representative_job = {}  # map a non-fake job id to its representative job
        self.implicit_map_jobs = []
        self.collection_types = {}

        self.hda_hid_in_history = {}
        self.hdca_hid_in_history = {}

        self.__summarize()

    def hid(self, object):
        if object.history_content_type == "dataset_collection":
            if object.id in self.hdca_hid_in_history:
                return self.hdca_hid_in_history[object.id]
            elif object.history == self.history:
                return object.hid
            else:
                log.warning("extraction issue, using hdca hid from outside current history and unmapped")
                return object.hid
        else:
            if object.id in self.hda_hid_in_history:
                return self.hda_hid_in_history[object.id]
            elif object.history == self.history:
                return object.hid
            else:
                log.warning("extraction issue, using hda hid from outside current history and unmapped")
                return object.hid

    def __summarize(self):
        # Make a first pass handle all singleton jobs, input dataset and dataset collections
        # just grab the implicitly mapped jobs and handle in second pass. Second pass is
        # needed because cannot allow selection of individual datasets from an implicit
        # mapping during extraction - you get the collection or nothing.
        for content in self.history.active_contents:
            self.__summarize_content(content)

    def __summarize_content(self, content):
        # Update internal state for history content (either an HDA or
        # an HDCA).
        if content.history_content_type == "dataset_collection":
            self.__summarize_dataset_collection(content)
        else:
            self.__summarize_dataset(content)

    def __summarize_dataset_collection(self, dataset_collection):
        hid_in_history = dataset_collection.hid
        dataset_collection = self.__original_hdca(dataset_collection)
        self.hdca_hid_in_history[dataset_collection.id] = hid_in_history

        hid = dataset_collection.hid
        self.collection_types[hid] = dataset_collection.collection.collection_type
        if cja := dataset_collection.creating_job_associations:
            # Use the "first" job to represent all mapped jobs.
            representative_assoc = cja[0]
            representative_job = representative_assoc.job
            if (
                representative_job not in self.jobs
                or self.jobs[representative_job][0][1].history_content_type == "dataset"
            ):
                self.jobs[representative_job] = [(representative_assoc.name, dataset_collection)]
                if dataset_collection.implicit_output_name:
                    self.implicit_map_jobs.append(representative_job)
            else:
                self.jobs[representative_job].append((representative_assoc.name, dataset_collection))
            for assoc in cja:
                job = assoc.job
                self.job_id2representative_job[job.id] = representative_job
        # This whole elif condition may no longer be needed do to additional
        # tracking with creating_job_associations. Will delete at some point.
        elif dataset_collection.implicit_output_name:
            # TODO: Optimize db call
            element = dataset_collection.collection.first_dataset_element
            if not element:
                # Got no dataset instance to walk back up to creating job.
                # TODO track this via tool request model
                job = DatasetCollectionCreationJob(dataset_collection)
                self.jobs[job] = [(None, dataset_collection)]
                return
            else:
                dataset_instance = element.hda
            if not self.__check_state(dataset_instance):
                # Just checking the state of one instance, don't need more but
                # makes me wonder if even need this check at all?
                return

            original_hda = self.__original_hda(dataset_instance)
            if not original_hda.creating_job_associations:
                log.warning(
                    "An implicitly create output dataset collection doesn't have a creating_job_association, should not happen!"
                )
                job = DatasetCollectionCreationJob(dataset_collection)
                self.jobs[job] = [(None, dataset_collection)]

            for assoc in original_hda.creating_job_associations:
                job = assoc.job
                if job not in self.jobs or self.jobs[job][0][1].history_content_type == "dataset":
                    self.jobs[job] = [(assoc.name, dataset_collection)]
                    self.job_id2representative_job[job.id] = job
                    self.implicit_map_jobs.append(job)
                else:
                    self.jobs[job].append((assoc.name, dataset_collection))
        else:
            job = DatasetCollectionCreationJob(dataset_collection)
            self.jobs[job] = [(None, dataset_collection)]

    def __summarize_dataset(self, dataset):
        if not self.__check_state(dataset):
            return

        hid_in_history = dataset.hid
        original_hda = self.__original_hda(dataset)
        self.hda_hid_in_history[original_hda.id] = hid_in_history

        if not original_hda.creating_job_associations:
            self.jobs[FakeJob(dataset)] = [(None, dataset)]

        for assoc in original_hda.creating_job_associations:
            job = assoc.job
            if job in self.jobs:
                self.jobs[job].append((assoc.name, dataset))
            else:
                self.jobs[job] = [(assoc.name, dataset)]
                self.job_id2representative_job[job.id] = job

    def __original_hdca(self, hdca):
        while hdca.copied_from_history_dataset_collection_association:
            hdca = hdca.copied_from_history_dataset_collection_association
        return hdca

    def __original_hda(self, hda):
        # if this hda was copied from another, we need to find the job that created the original hda
        while hda.copied_from_history_dataset_association:
            hda = hda.copied_from_history_dataset_association
        return hda

    def __check_state(self, hda):
        # FIXME: Create "Dataset.is_finished"
        if hda.state in ("new", "running", "queued"):
            self.warnings.add(WARNING_SOME_DATASETS_NOT_READY)
            return
        return hda


def step_inputs(trans, job):
    tool = trans.app.toolbox.get_tool(job.tool_id, tool_version=job.tool_version)
    param_values = job.get_param_values(
        trans.app, ignore_errors=True
    )  # If a tool was updated and e.g. had a text value changed to an integer, we don't want a traceback here
    associations = __cleanup_param_values(tool.inputs, param_values)
    tool_inputs = tool.params_to_strings(param_values, trans.app)
    return tool_inputs, associations


def __cleanup_param_values(inputs, values):
    """
    Remove 'Data' values from `param_values`, along with metadata cruft,
    but track the associations.
    """
    associations = []
    # dbkey is pushed in by the framework
    if "dbkey" in values:
        del values["dbkey"]
    root_values = values
    root_input_keys = inputs.keys()

    # Recursively clean data inputs and dynamic selects
    def cleanup(prefix, inputs, values):
        for key, input in inputs.items():
            if isinstance(input, DataToolParameter) or isinstance(input, DataCollectionToolParameter):
                items = values[key]
                values[key] = None
                # HACK: Nested associations are not yet working, but we
                #       still need to clean them up so we can serialize
                # if not( prefix ):
                for item in listify(items):
                    if isinstance(item, model.DatasetCollectionElement):
                        item = item.first_dataset_instance()
                    if item:  # this is false for a non-set optional dataset
                        associations.append((item.hid, prefix + key))

                # Cleanup the other deprecated crap associated with datasets
                # as well. Worse, for nested datasets all the metadata is
                # being pushed into the root. FIXME: MUST REMOVE SOON
                key = f"{prefix + key}_"
                for k in root_values.keys():
                    if k not in root_input_keys and k.startswith(key):
                        del root_values[k]
            elif isinstance(input, Repeat):
                if key in values:
                    group_values = values[key]
                    for i, rep_values in enumerate(group_values):
                        rep_index = rep_values["__index__"]
                        cleanup("%s%s_%d|" % (prefix, key, rep_index), input.inputs, group_values[i])
            elif isinstance(input, Conditional):
                # Scrub dynamic resource related parameters from workflows,
                # they cause problems and the workflow probably should include
                # their state in workflow encoding.
                if input.name == "__job_resource":
                    if input.name in values:
                        del values[input.name]
                    return
                if input.name in values:
                    group_values = values[input.name]
                    current_case = group_values["__current_case__"]
                    cleanup(f"{prefix}{key}|", input.cases[current_case].inputs, group_values)
            elif isinstance(input, Section):
                if input.name in values:
                    cleanup(f"{prefix}{key}|", input.inputs, values[input.name])

    cleanup("", inputs, values)
    return associations


__all__ = ("summarize", "extract_workflow")

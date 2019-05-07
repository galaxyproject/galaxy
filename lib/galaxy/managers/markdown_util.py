"""Utilities defining "Galaxy Flavored Markdown".

This is an extension of markdown designed to allow rendering Galaxy object
references.

The core "Galaxy Flavored Markdown" format should just reference objects
by encoded IDs - but preprocessing should allow for instance workflow objects
to be referenced relative to the workflow (inputs, outputs, steps, etc..) and
potential history flavor would allow objects to be referenced by HID. This
second idea is unimplemented, it is just an example of the general concept of
context specific processing.
"""
import logging
import re

from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.hdas import HDAManager
from galaxy.managers.hdcas import HDCASerializer
from galaxy.managers.jobs import JobManager
from galaxy.managers.workflows import WorkflowsManager

log = logging.getLogger(__name__)

GALAXY_FLAVORED_MARKDOWN_CONTAINERS = [
    "history_dataset_display",
    "history_dataset_collection_display",
    "history_dataset_as_image",
    "history_dataset_peek",
    "history_dataset_info",
    "workflow_display",
    "job_metrics",
    "job_parameters",
    "tool_stderr",
    "tool_stdout",
]
GALAXY_FLAVORED_MARKDOWN_CONTAINER_REGEX = "(%s)" % "|".join(GALAXY_FLAVORED_MARKDOWN_CONTAINERS)

FENCE_START = re.compile(r'```.*')
FENCE_END = re.compile(r'```[\w]*')

OUTPUT_LABEL_PATTERN = re.compile(r'output=([\w_\-]+)')
INPUT_LABEL_PATTERN = re.compile(r'input=([\w_\-]+)')
# STEP_OUTPUT_LABEL_PATTERN = re.compile(r'step_output=([\w_\-]+)/([\w_\-]+)')
STEP_LABEL_PATTERN = re.compile(r'step=([\w_\-]+)')
ID_PATTERN = re.compile(r'(workflow_id|history_dataset_id|history_dataset_collection_id|job_id)=([\d]+)')
GALAXY_FLAVORED_MARKDOWN_CONTAINER_LINE_PATTERN = re.compile(
    r":::\s+%s.*\n" % GALAXY_FLAVORED_MARKDOWN_CONTAINER_REGEX
)


def ready_galaxy_markdown_for_export(trans, internal_galaxy_markdown):
    """Fill in details needed to render Galaxy flavored markdown.

    Take it from a minimal internal version to an externally render-able version
    with more details populated and actual IDs replaced with encoded IDs to render
    external links. Return expanded markdown and extra data useful for rendering
    custom container tags.
    """
    hdas_manager = HDAManager(trans.app)
    workflows_manager = WorkflowsManager(trans.app)
    extra_rendering_data = {}

    def _remap(container, line):
        remap_lines = []
        id_match = re.search(ID_PATTERN, line)
        object_id = None
        encoded_id = None
        if id_match:
            object_id = int(id_match.group(2))
            encoded_id = trans.security.encode_id(object_id)
            line = line.replace(id_match.group(), "%s=%s" % (id_match.group(1), encoded_id))
        remap_lines.append(line)

        def remap_with_fenced_output(output, default):
            if output:
                remap_lines.append("```\n")
                for line in output.splitlines(True):
                    if not line.endswith("\n"):
                        line += "\n"
                    remap_lines.append(line)
                remap_lines.append("```\n")
            else:
                remap_lines.append("%s\n" % default)

        if container == "history_dataset_display":
            assert object_id is not None
            hda = hdas_manager.get_accessible(object_id, trans.user)
            if "history_datasets" not in extra_rendering_data:
                extra_rendering_data["history_datasets"] = {}
            extra_rendering_data["history_datasets"][encoded_id] = {
                "name": hda.name,
            }
        elif container == "history_dataset_peek":
            assert object_id is not None
            hda = hdas_manager.get_accessible(object_id, trans.user)
            peek = hda.peek
            remap_with_fenced_output(peek, "*No Dataset Peek Available*")
        elif container == "history_dataset_info":
            hda = hdas_manager.get_accessible(object_id, trans.user)
            info = hda.info
            remap_with_fenced_output(info, "*No Dataset Info Available*")
        elif container == "workflow_display":
            stored_workflow = workflows_manager.get_stored_accessible_workflow(trans, encoded_id, by_stored_id=False)
            if "workflows" not in extra_rendering_data:
                extra_rendering_data["workflows"] = {}
            extra_rendering_data["workflows"][encoded_id] = {
                "name": stored_workflow.name,
            }
        elif container == "history_dataset_collection_display":
            collection_manager = DatasetCollectionManager(trans.app)
            hdca = collection_manager.get_dataset_collection_instance(trans, "history", encoded_id)
            hdca_serializer = HDCASerializer(trans.app)
            hdca_view = hdca_serializer.serialize_to_view(
                hdca, user=trans.user, trans=trans, view="summary"
            )
            if "history_dataset_collections" not in extra_rendering_data:
                extra_rendering_data["history_dataset_collections"] = {}
            extra_rendering_data["history_dataset_collections"][encoded_id] = hdca_view
        elif container == "tool_stdout":
            job_manager = JobManager(trans.app)
            job = job_manager.get_accessible_job(trans, object_id)
            remap_with_fenced_output(job.tool_stdout, "*No Standard Output Available*")
        elif container == "tool_stderr":
            job_manager = JobManager(trans.app)
            job = job_manager.get_accessible_job(trans, object_id)
            remap_with_fenced_output(job.tool_stderr, "*No Standard Error Available*")
        return remap_lines

    export_markdown = _remap_galaxy_markdown_containers(_remap, internal_galaxy_markdown)
    log.info("export markdown is \n%s\n\nextra_rendering_data is %s" % (export_markdown, extra_rendering_data))
    return export_markdown, extra_rendering_data


def resolve_invocation_markdown(trans, invocation, workflow_markdown):
    """Resolve invocation objects to convert markdown to 'internal' representation.

    Replace references to workflow parts with actual inputs and outputs from executed
    workflow.
    """
    # Done:
    # convert output=name -to- history_dataset_id=<id> | history_dataset_collection_id=<id>
    # convert input=name -to- history_dataset_id=<id> | history_dataset_collection_id=<id>
    # TODO:
    # convert step=name -to- job_id=<id>
    # convert step_output=index/name -to- history_dataset_id=<id> | history_dataset_collection_id=<id>

    def _remap(container, line):
        if container == "workflow_display":
            return "::: workflow_display workflow_id=%s\n" % invocation.workflow.id
        ref_object_type = None
        output_match = re.search(OUTPUT_LABEL_PATTERN, line)
        input_match = re.search(INPUT_LABEL_PATTERN, line)
        step_match = re.search(STEP_LABEL_PATTERN, line)
        if output_match:
            target_match = output_match
            name = output_match.group(1)
            ref_object = invocation.get_output_object(name)
        elif input_match:
            target_match = input_match
            name = input_match.group(1)
            ref_object = invocation.get_input_object(name)
        elif step_match:
            target_match = step_match
            name = step_match.group(1)
            ref_object_type = "job"
            ref_object = invocation.step_invocation_for_label(name).job
        else:
            target_match = None
            ref_object = None
        if ref_object:
            if ref_object_type is None:
                if ref_object.history_content_type == "dataset":
                    ref_object_type = "history_dataset"
                else:
                    ref_object_type = "history_dataset_collection"
            line = line.replace(target_match.group(), "%s_id=%s" % (ref_object_type, ref_object.id))
        return line

    rval = _remap_galaxy_markdown_containers(_remap, workflow_markdown)
    log.info("workflow markdown is \n%s" % rval)
    return rval


def _remap_galaxy_markdown_containers(func, markdown):
    remapped_lines = []
    fenced = False
    for line in markdown.splitlines(True):
        if not fenced:
            if FENCE_START.match(line):
                fenced = True
                remapped_lines.append(line)
                continue
        elif fenced:
            if FENCE_END.match(line):
                fenced = False
            remapped_lines.append(line)
            continue

        container_match = GALAXY_FLAVORED_MARKDOWN_CONTAINER_LINE_PATTERN.match(line)
        if container_match:
            remap_line = func(container_match.group(1), line)
            if not isinstance(remap_line, list):
                remap_line = [remap_line]
            remapped_lines.extend(remap_line)
        else:
            remapped_lines.append(line)
    rval = "".join(remapped_lines)
    return rval


__all__ = (
    'ready_galaxy_markdown_for_export',
    'resolve_invocation_markdown',
)

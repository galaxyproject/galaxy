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
INVOCATION_SECTIONS = [
    "invocation_inputs",
    "invocation_outputs",
]
ALL_CONTAINER_TYPES = GALAXY_FLAVORED_MARKDOWN_CONTAINERS + INVOCATION_SECTIONS
GALAXY_FLAVORED_MARKDOWN_CONTAINER_REGEX = "(%s)" % "|".join(ALL_CONTAINER_TYPES)

ARG_VAL_REGEX = r'''[\w_\-]+|\"[^\"]+\"|\'[^\']+\''''
ARG_VAL_CAPTURED_REGEX = r'''(?:([\w_\-]+)|\"([^\"]+)\"|\'([^\']+)\')'''
FUNCTION_ARG = r'\s*\w+\s*=\s*(?:%s)\s*' % ARG_VAL_REGEX
FUNCTION_CALL_LINE_TEMPLATE = r'\s*%s\s*\((?:' + FUNCTION_ARG + r')?\)\s*'
GALAXY_MARKDOWN_FUNCTION_CALL_LINE = re.compile(FUNCTION_CALL_LINE_TEMPLATE % GALAXY_FLAVORED_MARKDOWN_CONTAINER_REGEX)

BLOCK_FENCE_START = re.compile(r'```.*')
BLOCK_FENCE_END = re.compile(r'```[\s]*')

OUTPUT_LABEL_PATTERN = re.compile(r'output=\s*%s\s*' % ARG_VAL_CAPTURED_REGEX)
INPUT_LABEL_PATTERN = re.compile(r'input=\s*%s\s*' % ARG_VAL_CAPTURED_REGEX)
STEP_LABEL_PATTERN = re.compile(r'step=\s*%s\s*' % ARG_VAL_CAPTURED_REGEX)
# STEP_OUTPUT_LABEL_PATTERN = re.compile(r'step_output=([\w_\-]+)/([\w_\-]+)')
ID_PATTERN = re.compile(r'(workflow_id|history_dataset_id|history_dataset_collection_id|job_id)=([\d]+)')
GALAXY_FLAVORED_MARKDOWN_CONTAINER_LINE_PATTERN = re.compile(
    r"```\s*galaxy\s*"
)
INVOCATION_SECTION_MARKDOWN_CONTAINER_LINE_PATTERN = re.compile(
    r"```\s*galaxy\s*"
)
GALAXY_FENCED_BLOCK = re.compile(r'^```\s*galaxy\s*(.*?)^```', re.MULTILINE ^ re.DOTALL)
VALID_CONTAINER_START_PATTERN = re.compile(r"^```\s+[\w]+.*$")
VALID_CONTAINER_END_PATTERN = re.compile(r"^```\s*$")
WHITE_SPACE_ONLY_PATTERN = re.compile(r"^[\s]+$")


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
        id_match = re.search(ID_PATTERN, line)
        object_id = None
        encoded_id = None
        if id_match:
            object_id = int(id_match.group(2))
            encoded_id = trans.security.encode_id(object_id)
            line = line.replace(id_match.group(), "%s=%s" % (id_match.group(1), encoded_id))

        def ensure_rendering_data_for(object_type, encoded_id):
            if object_type not in extra_rendering_data:
                extra_rendering_data[object_type] = {}
            object_type_data = extra_rendering_data[object_type]
            if encoded_id not in object_type_data:
                object_type_data[encoded_id] = {}
            return object_type_data[encoded_id]

        def extend_history_dataset_rendering_data(key, val, default_val):
            ensure_rendering_data_for("history_datasets", encoded_id)[key] = val or default_val

        if container == "history_dataset_display":
            assert object_id is not None
            hda = hdas_manager.get_accessible(object_id, trans.user)
            if "history_datasets" not in extra_rendering_data:
                extra_rendering_data["history_datasets"] = {}
            extend_history_dataset_rendering_data("name", hda.name, "")
        elif container == "history_dataset_peek":
            assert object_id is not None
            hda = hdas_manager.get_accessible(object_id, trans.user)
            peek = hda.peek
            extend_history_dataset_rendering_data("peek", peek, "*No Dataset Peek Available*")
        elif container == "history_dataset_info":
            hda = hdas_manager.get_accessible(object_id, trans.user)
            info = hda.info
            extend_history_dataset_rendering_data("info", info, "*No Dataset Peek Available*")
        elif container == "workflow_display":
            # TODO: should be workflow id...
            stored_workflow = workflows_manager.get_stored_accessible_workflow(trans, encoded_id)
            ensure_rendering_data_for("workflows", encoded_id)["name"] = stored_workflow.name
        elif container == "history_dataset_collection_display":
            collection_manager = DatasetCollectionManager(trans.app)
            hdca = collection_manager.get_dataset_collection_instance(trans, "history", encoded_id)
            hdca_serializer = HDCASerializer(trans.app)
            hdca_view = hdca_serializer.serialize_to_view(
                hdca, user=trans.user, trans=trans, view="summary"
            )
            if "history_dataset_collections" not in extra_rendering_data:
                extra_rendering_data["history_dataset_collections"] = {}
            ensure_rendering_data_for("history_dataset_collections", encoded_id).update(hdca_view)
        elif container == "tool_stdout":
            job_manager = JobManager(trans.app)
            job = job_manager.get_accessible_job(trans, object_id)
            ensure_rendering_data_for("jobs", encoded_id)["tool_stdout"] = job.tool_stdout or "*No Standard Output Available*"
        elif container == "tool_stderr":
            job_manager = JobManager(trans.app)
            job = job_manager.get_accessible_job(trans, object_id)
            ensure_rendering_data_for("jobs", encoded_id)["tool_stderr"] = job.tool_stderr or "*No Standard Error Available*"
        return (line, False)

    export_markdown = _remap_galaxy_markdown_calls(_remap, internal_galaxy_markdown)
    return export_markdown, extra_rendering_data


def resolve_invocation_markdown(trans, invocation, workflow_markdown):
    """Resolve invocation objects to convert markdown to 'internal' representation.

    Replace references to abstract workflow parts with actual galaxy object IDs corresponding
    to the actual executed workflow. For instance:

        convert output=name -to- history_dataset_id=<id> | history_dataset_collection_id=<id>
        convert input=name -to- history_dataset_id=<id> | history_dataset_collection_id=<id>
        convert step=name -to- job_id=<id>

    Also expand/convert workflow invocation specific container sections into actual Galaxy
    markdown - these containers include: invocation_inputs, invocation_outputs, invocation_workflow.
    Hopefully this list will be expanded to include invocation_qc.
    """
    # TODO: convert step outputs?
    # convert step_output=index/name -to- history_dataset_id=<id> | history_dataset_collection_id=<id>

    def _section_remap(container, line):
        section_markdown = ""
        if container == "invocation_outputs":
            for output_assoc in invocation.output_associations:
                if not output_assoc.workflow_output.label:
                    continue

                if output_assoc.history_content_type == "dataset":
                    section_markdown += """#### Output Dataset: %s
```galaxy
history_dataset_display(output="%s")
```
""" % (output_assoc.workflow_output.label, output_assoc.workflow_output.label)
                else:
                    section_markdown += """#### Output Dataset Collection: %s
```galaxy
history_dataset_collection_display(output="%s")
```
""" % (output_assoc.workflow_output.label)
        elif container == "invocation_inputs":
            for input_assoc in invocation.input_associations:
                if not input_assoc.workflow_step.label:
                    continue

                if input_assoc.history_content_type == "dataset":
                    section_markdown += """#### Input Dataset: %s
```galaxy
history_dataset_display(input="%s")
```
""" % (input_assoc.workflow_step.label, input_assoc.workflow_step.label)
                else:
                    section_markdown += """#### Input Dataset Collection: %s
```galaxy
history_dataset_collection_display(input=%s)
```
""" % (input_assoc.workflow_step.label, input_assoc.workflow_step.label)
        else:
            return line, False
        return section_markdown, True

    def _remap(container, line):
        if container == "workflow_display":
            # TODO: this really should be workflow id not stored workflow id but the API
            # it consumes wants the stored id.
            return ("workflow_display(workflow_id=%s)\n" % invocation.workflow.stored_workflow.id, False)
        ref_object_type = None
        output_match = re.search(OUTPUT_LABEL_PATTERN, line)
        input_match = re.search(INPUT_LABEL_PATTERN, line)
        step_match = re.search(STEP_LABEL_PATTERN, line)

        def find_non_empty_group(match):
            for group in match.groups():
                if group:
                    return group

        if output_match:
            target_match = output_match
            name = find_non_empty_group(target_match)
            ref_object = invocation.get_output_object(name)
        elif input_match:
            target_match = input_match
            name = find_non_empty_group(target_match)
            ref_object = invocation.get_input_object(name)
        elif step_match:
            target_match = step_match
            name = find_non_empty_group(target_match)
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
        return (line, False)

    log.debug("workflow markdown is \n%s" % workflow_markdown)
    workflow_markdown = _remap_galaxy_markdown_calls(
        _section_remap,
        workflow_markdown,
    )
    galaxy_markdown = _remap_galaxy_markdown_calls(_remap, workflow_markdown)
    log.debug("galaxy markdown is \n%s" % galaxy_markdown)
    return galaxy_markdown


def validate_galaxy_markdown(galaxy_markdown, internal=True):
    expecting_container_close_for = None
    last_line_no = 0
    function_calls = 0
    for (line, fenced, open_fence, line_no) in _split_markdown_lines(galaxy_markdown):
        last_line_no = line_no

        def invalid_line(template, **kwd):
            if "line" in kwd:
                kwd["line"] = line.rstrip("\r\n")
            raise Exception("Invalid line %d: %s" % (line_no + 1, template.format(**kwd)))

        expecting_container_close = expecting_container_close_for is not None
        if not fenced and expecting_container_close:
            invalid_line("[{line}] is not expected close line for [{expected_for}]", line=line, expected_for=expecting_container_close_for)
            continue
        elif not fenced:
            continue
        elif fenced and expecting_container_close and BLOCK_FENCE_END.match(line):
            expecting_container_close_for = None
        elif open_fence and GALAXY_FLAVORED_MARKDOWN_CONTAINER_LINE_PATTERN.match(line):
            if expecting_container_close:
                if not VALID_CONTAINER_END_PATTERN.match(line):
                    invalid_line("Invalid command close line [{line}] for [{expected_for}]", line=line, expected_for=expecting_container_close_for)
                # else closing container and we're done
                expecting_container_close_for = None
                continue

            expecting_container_close_for = line
            continue
        elif fenced and line and expecting_container_close_for:
            if GALAXY_MARKDOWN_FUNCTION_CALL_LINE.match(line):
                function_calls += 1
                if function_calls > 1:
                    invalid_line("Only one Galaxy directive is allowed per fenced Galaxy block (```galaxy)")
                continue
            else:
                invalid_line("Invalid embedded Galaxy markup line [{line}]", line=line)

        # Markdown unrelated to Galaxy object containers.
        continue

    if expecting_container_close_for:
        raise Exception("Invalid line %d: %s" % (last_line_no, "close of block for [{expected_for}] expected".format(expected_for=expecting_container_close_for)))


def _remap_galaxy_markdown_containers(func, markdown):
    new_markdown = markdown

    searching_from = 0
    while True:
        from_markdown = new_markdown[searching_from:]
        match = re.search(GALAXY_FENCED_BLOCK, from_markdown)
        if match is not None:
            replace = match.group(1)
            (replacement, whole_block) = func(replace)
            if whole_block:
                start_pos = match.start()
                end_pos = match.end()
            else:
                start_pos = match.start(1)
                end_pos = match.end(1)
            start_pos = start_pos + searching_from
            end_pos = end_pos + searching_from

            new_markdown = new_markdown[:start_pos] + replacement + new_markdown[end_pos:]
            searching_from = start_pos + len(replacement)
        else:
            break

    return new_markdown


def _remap_galaxy_markdown_calls(func, markdown):

    def _remap_container(container):
        matching_line = None
        for line in container.splitlines():
            if GALAXY_MARKDOWN_FUNCTION_CALL_LINE.match(line):
                assert matching_line is None
                matching_line = line

        assert matching_line, "Failed to find func call line in [%s]" % container
        match = GALAXY_MARKDOWN_FUNCTION_CALL_LINE.match(line)

        return func(match.group(1), matching_line + "\n")

    return _remap_galaxy_markdown_containers(_remap_container, markdown)


def _split_markdown_lines(markdown):
    """Yield lines of a markdown document line-by-line keeping track of fencing.

    'Fenced' lines are code-like block (e.g. between ```) that shouldn't contain
    Markdown markup.
    """
    block_fenced = False
    indent_fenced = False
    for line_number, line in enumerate(markdown.splitlines(True)):
        open_fence_this_iteration = False
        indent_fenced = line.startswith("    ") or (indent_fenced and WHITE_SPACE_ONLY_PATTERN.match(line))
        if not block_fenced:
            if BLOCK_FENCE_START.match(line):
                open_fence_this_iteration = True
                block_fenced = True
        yield (line, block_fenced or indent_fenced, open_fence_this_iteration, line_number)
        if not open_fence_this_iteration and BLOCK_FENCE_END.match(line):
            block_fenced = False


__all__ = (
    'ready_galaxy_markdown_for_export',
    'resolve_invocation_markdown',
)

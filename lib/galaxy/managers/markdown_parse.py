"""Utilities for parsing "Galaxy Flavored Markdown".

See markdown_util.py for loading objects and interacting with the rest of Galaxy.
This file is meant to be relatively self contained and just used to "parse" and validate
Galaxy Markdown. Keeping things isolated to allow re-use of these utilities in other
projects (e.g. gxformat2).
"""
import re

BLOCK_FENCE_START = re.compile(r'```.*')
BLOCK_FENCE_END = re.compile(r'```[\s]*')
GALAXY_FLAVORED_MARKDOWN_CONTAINER_LINE_PATTERN = re.compile(
    r"```\s*galaxy\s*"
)
VALID_CONTAINER_END_PATTERN = re.compile(r"^```\s*$")
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
FUNCTION_ARG = r'\s*\w+\s*=\s*(?:%s)\s*' % ARG_VAL_REGEX
FUNCTION_CALL_LINE_TEMPLATE = r'\s*%s\s*\((?:' + FUNCTION_ARG + r')?\)\s*'
GALAXY_MARKDOWN_FUNCTION_CALL_LINE = re.compile(FUNCTION_CALL_LINE_TEMPLATE % GALAXY_FLAVORED_MARKDOWN_CONTAINER_REGEX)
WHITE_SPACE_ONLY_PATTERN = re.compile(r"^[\s]+$")


def validate_galaxy_markdown(galaxy_markdown, internal=True):
    """Validate the supplied markdown and throw an ValueError with reason if invalid."""
    expecting_container_close_for = None
    last_line_no = 0
    function_calls = 0
    for (line, fenced, open_fence, line_no) in _split_markdown_lines(galaxy_markdown):
        last_line_no = line_no

        def invalid_line(template, **kwd):
            if "line" in kwd:
                kwd["line"] = line.rstrip("\r\n")
            raise ValueError("Invalid line %d: %s" % (line_no + 1, template.format(**kwd)))

        expecting_container_close = expecting_container_close_for is not None
        if not fenced and expecting_container_close:
            invalid_line("[{line}] is not expected close line for [{expected_for}]", line=line, expected_for=expecting_container_close_for)
            continue
        elif not fenced:
            continue
        elif fenced and expecting_container_close and BLOCK_FENCE_END.match(line):
            # reset
            expecting_container_close_for = None
            function_calls = 0
        elif open_fence and GALAXY_FLAVORED_MARKDOWN_CONTAINER_LINE_PATTERN.match(line):
            if expecting_container_close:
                if not VALID_CONTAINER_END_PATTERN.match(line):
                    invalid_line("Invalid command close line [{line}] for [{expected_for}]", line=line, expected_for=expecting_container_close_for)
                # else closing container and we're done
                expecting_container_close_for = None
                function_calls = 0
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
        template = "Invalid line %d: %s"
        msg = template % (last_line_no, "close of block for [{expected_for}] expected".format(expected_for=expecting_container_close_for))
        raise ValueError(msg)


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
    'validate_galaxy_markdown',
    'GALAXY_MARKDOWN_FUNCTION_CALL_LINE',
)

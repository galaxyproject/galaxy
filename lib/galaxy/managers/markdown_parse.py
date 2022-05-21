"""Utilities for parsing "Galaxy Flavored Markdown".

See markdown_util.py for loading objects and interacting with the rest of Galaxy.
This file is meant to be relatively self contained and just used to "parse" and validate
Galaxy Markdown. Keeping things isolated to allow re-use of these utilities in other
projects (e.g. gxformat2).
"""
import re
from typing import (
    cast,
    Dict,
    List,
    Union,
)

BLOCK_FENCE_START = re.compile(r"```.*")
BLOCK_FENCE_END = re.compile(r"```[\s]*")
GALAXY_FLAVORED_MARKDOWN_CONTAINER_LINE_PATTERN = re.compile(r"```\s*galaxy\s*")
VALID_CONTAINER_END_PATTERN = re.compile(r"^```\s*$")


class DynamicArguments:
    pass


DYNAMIC_ARGUMENTS = DynamicArguments()
VALID_ARGUMENTS: Dict[str, Union[List[str], DynamicArguments]] = {
    "history_link": ["history_id"],
    "history_dataset_display": ["input", "output", "history_dataset_id"],
    "history_dataset_embedded": ["input", "output", "history_dataset_id"],
    "history_dataset_as_image": ["input", "output", "history_dataset_id", "path"],
    "history_dataset_peek": ["input", "output", "history_dataset_id"],
    "history_dataset_info": ["input", "output", "history_dataset_id"],
    "history_dataset_link": ["input", "output", "history_dataset_id", "path", "label"],
    "history_dataset_index": ["input", "output", "history_dataset_id", "path"],
    "history_dataset_name": ["input", "output", "history_dataset_id"],
    "history_dataset_type": ["input", "output", "history_dataset_id"],
    "history_dataset_collection_display": ["input", "output", "history_dataset_collection_id"],
    "workflow_display": ["workflow_id"],
    "job_metrics": ["step", "job_id"],
    "job_parameters": ["step", "job_id"],
    "tool_stderr": ["step", "job_id"],
    "tool_stdout": ["step", "job_id"],
    "generate_galaxy_version": [],
    "generate_time": [],
    "visualization": DYNAMIC_ARGUMENTS,
    # Invocation Flavored Markdown
    "invocation_time": ["invocation_id"],
    "invocation_outputs": [],
    "invocation_inputs": [],
}
GALAXY_FLAVORED_MARKDOWN_CONTAINERS = list(VALID_ARGUMENTS.keys())
GALAXY_FLAVORED_MARKDOWN_CONTAINER_REGEX = r"(?P<container>%s)" % "|".join(GALAXY_FLAVORED_MARKDOWN_CONTAINERS)

ARG_VAL_REGEX = r"""[\w_\-]+|\"[^\"]+\"|\'[^\']+\'"""
FUNCTION_ARG = r"\s*[\w\|]+\s*=\s*(?:%s)\s*" % ARG_VAL_REGEX
# embed commas between arguments
FUNCTION_MULTIPLE_ARGS = rf"(?P<firstargcall>{FUNCTION_ARG})(?P<restargcalls>(?:,{FUNCTION_ARG})*)"
FUNCTION_MULTIPLE_ARGS_PATTERN = re.compile(FUNCTION_MULTIPLE_ARGS)
FUNCTION_CALL_LINE_TEMPLATE = f"\\s*%s\\s*\\((?:{FUNCTION_MULTIPLE_ARGS})?\\)\\s*"
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
            invalid_line(
                "[{line}] is not expected close line for [{expected_for}]",
                line=line,
                expected_for=expecting_container_close_for,
            )
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
                    invalid_line(
                        "Invalid command close line [{line}] for [{expected_for}]",
                        line=line,
                        expected_for=expecting_container_close_for,
                    )
                # else closing container and we're done
                expecting_container_close_for = None
                function_calls = 0
                continue

            expecting_container_close_for = line
            continue
        elif fenced and line and expecting_container_close_for:
            func_call_match = GALAXY_MARKDOWN_FUNCTION_CALL_LINE.match(line)
            if func_call_match:
                function_calls += 1
                if function_calls > 1:
                    invalid_line("Only one Galaxy directive is allowed per fenced Galaxy block (```galaxy)")
                container = func_call_match.group("container")
                valid_args_raw = VALID_ARGUMENTS[container]
                if isinstance(valid_args_raw, DynamicArguments):
                    continue
                valid_args = cast(List[str], valid_args_raw)

                first_arg_call = func_call_match.group("firstargcall")

                def _validate_arg(arg_str):
                    if arg_str is not None:
                        arg_name = arg_str.split("=", 1)[0].strip()
                        if arg_name not in valid_args:
                            invalid_line("Invalid argument to Galaxy directive [{argument}]", argument=arg_name)

                _validate_arg(first_arg_call)
                rest = func_call_match.group("restargcalls")
                while rest:
                    rest = rest.strip().split(",", 1)[1]
                    arg_match = FUNCTION_MULTIPLE_ARGS_PATTERN.match(rest)
                    if not arg_match:
                        break
                    first_arg_call = arg_match.group("firstargcall")
                    _validate_arg(first_arg_call)
                    rest = arg_match.group("restargcalls")

                continue
            else:
                invalid_line("Invalid embedded Galaxy markup line [{line}]", line=line)

        # Markdown unrelated to Galaxy object containers.
        continue

    if expecting_container_close_for:
        template = "Invalid line %d: %s"
        msg = template % (last_line_no, f"close of block for [{expecting_container_close_for}] expected")
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
        indent_fenced = bool(line.startswith("    ") or (indent_fenced and WHITE_SPACE_ONLY_PATTERN.match(line)))
        if not block_fenced:
            if BLOCK_FENCE_START.match(line):
                open_fence_this_iteration = True
                block_fenced = True
        yield (line, block_fenced or indent_fenced, open_fence_this_iteration, line_number)
        if not open_fence_this_iteration and BLOCK_FENCE_END.match(line):
            block_fenced = False


__all__ = (
    "validate_galaxy_markdown",
    "GALAXY_MARKDOWN_FUNCTION_CALL_LINE",
)

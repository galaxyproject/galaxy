"""Utilities for parsing "Galaxy Flavored Markdown".

See markdown_util.py for loading objects and interacting with the rest of Galaxy.
This file is meant to be relatively self contained and just used to "parse" and validate
Galaxy Markdown. Keeping things isolated to allow re-use of these utilities in other
projects (e.g. gxformat2).
"""

import re

from ._markdown_directives import (
    DYNAMIC_ARGUMENTS,
    DynamicArguments,
    EMBED_CAPABLE_DIRECTIVES,
    SHARED_ARGUMENTS,
    VALID_ARGUMENTS,
)

BLOCK_FENCE_START = re.compile(r"```.*")
BLOCK_FENCE_END = re.compile(r"```[\s]*")
GALAXY_FLAVORED_MARKDOWN_CONTAINER_LINE_PATTERN = re.compile(r"```\s*galaxy\s*")
VALID_CONTAINER_END_PATTERN = re.compile(r"^```\s*$")

# The directive registry imported above (DynamicArguments, VALID_ARGUMENTS,
# EMBED_CAPABLE_DIRECTIVES, SHARED_ARGUMENTS) is generated from
# client/src/components/Markdown/directives.yml by scripts/markdown_directives_doc.py.
# Edit directives.yml and regenerate; do not edit _markdown_directives.py by hand.

GALAXY_FLAVORED_MARKDOWN_CONTAINERS = list(VALID_ARGUMENTS.keys())
GALAXY_FLAVORED_MARKDOWN_CONTAINER_REGEX = r"(?P<container>{})".format("|".join(GALAXY_FLAVORED_MARKDOWN_CONTAINERS))
GALAXY_FLAVORED_MARKDOWN_EMBED_CONTAIN_REGEX = r"(?P<container>{})".format("|".join(EMBED_CAPABLE_DIRECTIVES))

ARG_VAL_REGEX = r"""[\w_\-]+|\"[^\"]+\"|\'[^\']+\'"""
FUNCTION_ARG = rf"\s*[\w\|]+\s*=\s*(?:{ARG_VAL_REGEX})\s*"
# embed commas between arguments
FUNCTION_MULTIPLE_ARGS = rf"(?P<firstargcall>{FUNCTION_ARG})(?P<restargcalls>(?:,{FUNCTION_ARG})*)"
FUNCTION_MULTIPLE_ARGS_PATTERN = re.compile(FUNCTION_MULTIPLE_ARGS)
FUNCTION_CALL_LINE_TEMPLATE = f"\\s*%s\\s*\\((?:{FUNCTION_MULTIPLE_ARGS})?\\)\\s*"
GALAXY_MARKDOWN_FUNCTION_CALL_LINE = re.compile(FUNCTION_CALL_LINE_TEMPLATE % GALAXY_FLAVORED_MARKDOWN_CONTAINER_REGEX)
WHITE_SPACE_ONLY_PATTERN = re.compile(r"^[\s]+$")

GALAXY_MARKDOWN_EMBED_FUNCTION_CALL_LINE = FUNCTION_CALL_LINE_TEMPLATE % GALAXY_FLAVORED_MARKDOWN_EMBED_CONTAIN_REGEX
GALAXY_MARKDOWN_EMBED_FUNCTION_CALL_LINE_PATT = re.compile(GALAXY_MARKDOWN_EMBED_FUNCTION_CALL_LINE)
EMBED_DIRECTIVE_REGEX = re.compile(r"\$\{galaxy\s+%s\}" % GALAXY_MARKDOWN_EMBED_FUNCTION_CALL_LINE)  # noqa: UP031
EMBED_DIRECTIVE_REGEX_ANY = re.compile(r"\$\{galaxy\s+.*\}")


def validate_galaxy_markdown(galaxy_markdown, internal=True):
    """Validate the supplied markdown and throw an ValueError with reason if invalid."""

    expecting_container_close_for = None
    last_line_no = 0
    function_calls = 0
    for line, fenced, open_fence, line_no in _split_markdown_lines(galaxy_markdown):
        last_line_no = line_no

        expecting_container_close = expecting_container_close_for is not None
        if not fenced and expecting_container_close:
            _invalid_line(
                "[{line}] is not expected close line for [{expected_for}]",
                line_no,
                line=line,
                expected_for=expecting_container_close_for,
            )
            continue
        elif not fenced:
            first_match_any = EMBED_DIRECTIVE_REGEX_ANY.search(line)
            first_match = EMBED_DIRECTIVE_REGEX.search(line)
            if first_match_any:
                if not first_match:
                    _invalid_line(
                        "[{line}] contains invalid template expansion",
                        line_no,
                        line=line,
                    )
                else:
                    _check_func_call(first_match, line_no)
        elif fenced and expecting_container_close and BLOCK_FENCE_END.match(line):
            # reset
            expecting_container_close_for = None
            function_calls = 0
        elif open_fence and GALAXY_FLAVORED_MARKDOWN_CONTAINER_LINE_PATTERN.match(line):
            if expecting_container_close:
                if not VALID_CONTAINER_END_PATTERN.match(line):
                    _invalid_line(
                        "Invalid command close line [{line}] for [{expected_for}]",
                        line_no,
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
                    _invalid_line("Only one Galaxy directive is allowed per fenced Galaxy block (```galaxy)", line_no)
                _check_func_call(func_call_match, line_no)
            else:
                _invalid_line("Invalid embedded Galaxy markup line [{line}]", line_no, line=line)

        # Markdown unrelated to Galaxy object containers.
        continue

    if expecting_container_close_for:
        template = "Invalid line %d: %s"
        msg = template % (last_line_no, f"close of block for [{expecting_container_close_for}] expected")
        raise ValueError(msg)


def _invalid_line(template: str, line_no: int, **kwd):
    if "line" in kwd:
        kwd["line"] = kwd["line"].rstrip("\r\n")
    raise ValueError(f"Invalid line {line_no + 1}: {template.format(**kwd)}")


def _validate_arg(arg_str: str, valid_args, line_no: int):
    if arg_str is not None:
        arg_name = arg_str.split("=", 1)[0].strip()
        if arg_name not in valid_args and arg_name not in SHARED_ARGUMENTS:
            _invalid_line("Invalid argument to Galaxy directive [{argument}]", line_no, argument=arg_name)


def _check_func_call(func_call_match, line_no):
    container = func_call_match.group("container")
    valid_args = VALID_ARGUMENTS[container]
    if isinstance(valid_args, DynamicArguments):
        return

    first_arg_call = func_call_match.group("firstargcall")

    _validate_arg(first_arg_call, valid_args, line_no)
    rest = func_call_match.group("restargcalls")
    while rest:
        rest = rest.strip().split(",", 1)[1]
        arg_match = FUNCTION_MULTIPLE_ARGS_PATTERN.match(rest)
        if not arg_match:
            break
        first_arg_call = arg_match.group("firstargcall")
        _validate_arg(first_arg_call, valid_args, line_no)
        rest = arg_match.group("restargcalls")


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
    # Re-exported registry generated from directives.yml (see _markdown_directives).
    "DYNAMIC_ARGUMENTS",
    "DynamicArguments",
    "EMBED_CAPABLE_DIRECTIVES",
    "SHARED_ARGUMENTS",
    "VALID_ARGUMENTS",
)

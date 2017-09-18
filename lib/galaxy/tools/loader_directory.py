"""Utilities for loading and reasoning about unparsed tools in directories."""
import fnmatch
import glob
import logging
import os
import re
import sys

import yaml

from galaxy.util import checkers
from .parser import get_tool_source
from ..tools import loader

log = logging.getLogger(__name__)

PATH_DOES_NOT_EXIST_ERROR = "Could not load tools from path [%s] - this path does not exist."
PATH_AND_RECURSIVE_ERROR = "Cannot specify a single file and recursive."
LOAD_FAILURE_ERROR = "Failed to load tool with path %s."
TOOL_LOAD_ERROR = object()
TOOL_REGEX = re.compile(r"<tool\s")

YAML_EXTENSIONS = [".yaml", ".yml", ".json"]
CWL_EXTENSIONS = YAML_EXTENSIONS + [".cwl"]
EXCLUDE_WALK_DIRS = ['.hg', '.git', '.venv']


def load_exception_handler(path, exc_info):
    """Default exception handler for use by load_tool_elements_from_path."""
    log.warning(LOAD_FAILURE_ERROR % path, exc_info=exc_info)


def find_possible_tools_from_path(
    path,
    recursive=False,
    enable_beta_formats=False,
):
    """Walk a directory and find potential tool files."""
    possible_tool_files = []
    for possible_tool_file in _find_tool_files(
        path, recursive=recursive,
        enable_beta_formats=enable_beta_formats
    ):
        try:
            does_look_like_a_tool = looks_like_a_tool(
                possible_tool_file,
                enable_beta_formats=enable_beta_formats
            )
        except IOError:
            # Some problem reading the tool file, skip.
            continue

        if does_look_like_a_tool:
            possible_tool_files.append(possible_tool_file)

    return possible_tool_files


def load_tool_sources_from_path(
    path,
    load_exception_handler=load_exception_handler,
    recursive=False,
    register_load_errors=False,
):
    """Walk a directory and ToolSource objects."""
    return _load_tools_from_path(
        path,
        load_exception_handler=load_exception_handler,
        recursive=recursive,
        register_load_errors=register_load_errors,
        loader_func=get_tool_source,
        enable_beta_formats=True,
    )


def load_tool_elements_from_path(
    path,
    load_exception_handler=load_exception_handler,
    recursive=False,
    register_load_errors=False,
):
    """Walk a directory and load tool XML elements."""
    return _load_tools_from_path(
        path,
        load_exception_handler=load_exception_handler,
        recursive=recursive,
        register_load_errors=register_load_errors,
        loader_func=loader.load_tool,
        enable_beta_formats=False,
    )


def _load_tools_from_path(
    path,
    load_exception_handler,
    recursive,
    register_load_errors,
    loader_func,
    enable_beta_formats,
):
    loaded_objects = []
    for possible_tool_file in find_possible_tools_from_path(
        path,
        recursive=recursive,
        enable_beta_formats=enable_beta_formats,
    ):
        try:
            tool_element = loader_func(possible_tool_file)
            loaded_objects.append((possible_tool_file, tool_element))
        except Exception:
            exc_info = sys.exc_info()
            load_exception_handler(possible_tool_file, exc_info)
            if register_load_errors:
                loaded_objects.append((possible_tool_file, TOOL_LOAD_ERROR))
    return loaded_objects


def is_tool_load_error(obj):
    """Predicate to determine if object loaded for tool is a tool error."""
    return obj is TOOL_LOAD_ERROR


def looks_like_a_tool(path_or_uri_like, invalid_names=[], enable_beta_formats=False):
    """Quick check to see if a file looks like it may be a tool file.

    Whether true in a strict sense or not, lets say the intention and
    purpose of this procedure is to serve as a filter - all valid tools must
    "looks_like_a_tool" but not everything that looks like a tool is actually
    a valid tool.

    invalid_names may be supplied in the context of the tool shed to quickly
    rule common tool shed XML files.
    """
    path = resolved_path(path_or_uri_like)
    if path is UNRESOLVED_URI:
        # Assume the path maps to a real tool.
        return True

    looks = False

    if os.path.basename(path) in invalid_names:
        return False

    if looks_like_a_tool_xml(path):
        looks = True

    if not looks and enable_beta_formats:
        for tool_checker in BETA_TOOL_CHECKERS.values():
            if tool_checker(path):
                looks = True
                break

    return looks


def looks_like_a_tool_xml(path):
    """Quick check to see if a file looks like it may be a Galaxy XML tool file."""
    full_path = os.path.abspath(path)

    if not full_path.endswith(".xml"):
        return False

    if not os.path.getsize(full_path):
        return False

    if(checkers.check_binary(full_path) or
       checkers.check_image(full_path) or
       checkers.check_gzip(full_path)[0] or
       checkers.check_bz2(full_path)[0] or
       checkers.check_zip(full_path)):
        return False

    with open(path, "r") as f:
        start_contents = f.read(5 * 1024)
        if TOOL_REGEX.search(start_contents):
            return True

    return False


def is_a_yaml_with_class(path, classes):
    """Determine if a file is a valid YAML with a supplied ``class`` entry."""
    if not _has_extension(path, YAML_EXTENSIONS):
        return False

    with open(path, "r") as f:
        try:
            as_dict = yaml.safe_load(f)
        except Exception:
            return False

    if not isinstance(as_dict, dict):
        return False

    file_class = as_dict.get("class", None)
    return file_class in classes


def looks_like_a_tool_yaml(path):
    """Quick check to see if a file looks like it may be a Galaxy YAML tool file."""
    return is_a_yaml_with_class(path, ["GalaxyTool"])


def looks_like_a_cwl_artifact(path, classes=None):
    """Quick check to see if a file looks like it may be a CWL artifact."""
    if not _has_extension(path, CWL_EXTENSIONS):
        return False

    with open(path, "r") as f:
        try:
            as_dict = yaml.safe_load(f)
        except Exception:
            return False

    if not isinstance(as_dict, dict):
        return False

    file_class = as_dict.get("class", None)
    if classes is not None and file_class not in classes:
        return False

    file_cwl_version = as_dict.get("cwlVersion", None)
    return file_cwl_version is not None


def looks_like_a_tool_cwl(path):
    """Quick check to see if a file looks like it may be a CWL tool."""
    return looks_like_a_cwl_artifact(path, classes=["CommandLineTool", "ExpressionTool"])


def _find_tool_files(path_or_uri_like, recursive, enable_beta_formats):
    path = resolved_path(path_or_uri_like)
    if path is UNRESOLVED_URI:
        # Pass the URI through and assume it maps to a real tool.
        return [path_or_uri_like]

    is_file = not os.path.isdir(path)
    if not os.path.exists(path):
        raise Exception(PATH_DOES_NOT_EXIST_ERROR)
    elif is_file and recursive:
        raise Exception(PATH_AND_RECURSIVE_ERROR)
    elif is_file:
        return [os.path.abspath(path)]
    else:
        if enable_beta_formats:
            if not recursive:
                files = glob.glob(path + "/*")
            else:
                files = _find_files(path, "*")
        else:
            if not recursive:
                files = glob.glob(path + "/*.xml")
            else:
                files = _find_files(path, "*.xml")
        return [os.path.abspath(_) for _ in files]


def _has_extension(path, extensions):
    return any(path.endswith(e) for e in extensions)


def _find_files(directory, pattern='*'):
    if not os.path.exists(directory):
        raise ValueError("Directory not found {}".format(directory))

    matches = []
    for root, dirnames, filenames in os.walk(directory):
        # exclude some directories (like .hg) from traversing
        dirnames[:] = [dir for dir in dirnames if dir not in EXCLUDE_WALK_DIRS]
        for filename in filenames:
            full_path = os.path.join(root, filename)
            if fnmatch.filter([full_path], pattern):
                matches.append(os.path.join(root, filename))
    return matches


UNRESOLVED_URI = object()


def resolved_path(path_or_uri_like):
    """If this is a simple file path, return the path else UNRESOLVED_URI."""
    if "://" not in path_or_uri_like:
        return path_or_uri_like
    elif path_or_uri_like.startswith("file://"):
        return path_or_uri_like[len("file://"):]
    else:
        return UNRESOLVED_URI


BETA_TOOL_CHECKERS = {
    'yaml': looks_like_a_tool_yaml,
    'cwl': looks_like_a_tool_cwl,
}

__all__ = (
    "find_possible_tools_from_path",
    "is_a_yaml_with_class",
    "is_tool_load_error",
    "load_tool_elements_from_path",
    "load_tool_sources_from_path",
    "looks_like_a_cwl_artifact",
    "looks_like_a_tool_cwl",
    "looks_like_a_tool_xml",
    "looks_like_a_tool_yaml",
)

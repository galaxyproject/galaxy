import fnmatch
import glob
import os
import re
from ..tools import loader

import sys

import logging
log = logging.getLogger(__name__)

PATH_DOES_NOT_EXIST_ERROR = "Could not load tools from path [%s] - this path does not exist."
PATH_AND_RECURSIVE_ERROR = "Cannot specify a single file and recursive."
LOAD_FAILURE_ERROR = "Failed to load tool with path %s."
TOOL_LOAD_ERROR = object()
TOOL_REGEX = re.compile(r"<tool\s")


def load_exception_handler(path, exc_info):
    log.warn(LOAD_FAILURE_ERROR % path, exc_info=exc_info)


def load_tool_elements_from_path(
    path,
    load_exception_handler=load_exception_handler,
    recursive=False,
    register_load_errors=False,
):
    tool_elements = []
    for file in __find_tool_files(path, recursive=recursive):
        try:
            looks_like_a_tool = __looks_like_a_tool(file)
        except IOError:
            # Some problem reading the tool file, skip.
            continue

        if looks_like_a_tool:
            try:
                tool_elements.append((file, loader.load_tool(file)))
            except Exception:
                exc_info = sys.exc_info()
                load_exception_handler(file, exc_info)
                if register_load_errors:
                    tool_elements.append((file, TOOL_LOAD_ERROR))
    return tool_elements


def is_tool_load_error(obj):
    return obj is TOOL_LOAD_ERROR


def __looks_like_a_tool(path):
    with open(path, "r") as f:
        start_contents = f.read(5 * 1024)
        if TOOL_REGEX.search(start_contents):
            return True
    return False


def __find_tool_files(path, recursive):
    is_file = not os.path.isdir(path)
    if not os.path.exists(path):
        raise Exception(PATH_DOES_NOT_EXIST_ERROR)
    elif is_file and recursive:
        raise Exception(PATH_AND_RECURSIVE_ERROR)
    elif is_file:
        return [os.path.abspath(path)]
    else:
        if not recursive:
            files = glob.glob(path + "/*.xml")
        else:
            files = _find_files(path, "*.xml")
        return map(os.path.abspath, files)


def _find_files(directory, pattern='*'):
    if not os.path.exists(directory):
        raise ValueError("Directory not found {}".format(directory))

    matches = []
    for root, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            if fnmatch.filter([full_path], pattern):
                matches.append(os.path.join(root, filename))
    return matches

import glob
import os
from ..tools import loader

import sys

import logging
log = logging.getLogger(__name__)

PATH_DOES_NOT_EXIST_ERROR = "Could not load tools from path [%s] - this path does not exist."
LOAD_FAILURE_ERROR = "Failed to load tool with path %s."


def load_exception_handler(path, exc_info):
    log.warn(LOAD_FAILURE_ERROR % path, exc_info=exc_info)


def load_tool_elements_from_path(path, load_exception_handler=load_exception_handler):
    tool_elements = []
    for file in __find_tool_files(path):
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
    return tool_elements


def __looks_like_a_tool(path):
    with open(path) as f:
        for i in range(10):
            try:
                line = f.next()
            except StopIteration:
                break
            if "<tool" in line:
                return True
    return False


def __find_tool_files(path):
    if not os.path.exists(path):
        raise Exception(PATH_DOES_NOT_EXIST_ERROR)
    if not os.path.isdir(path):
        return [os.path.abspath(path)]
    else:
        return map(os.path.abspath, glob.glob(path + "/**.xml"))

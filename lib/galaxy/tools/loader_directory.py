import glob
import os
from ..tools import loader

PATH_DOES_NOT_EXIST_ERROR = "Could not load tools from path [%s] - this path does not exist."


def load_tool_elements_from_path(path):
    tool_elements = []
    for file in __find_tool_files(path):
        if __looks_like_a_tool(file):
            tool_elements.append((file, loader.load_tool(file)))
    return tool_elements


def __looks_like_a_tool(path):
    with open(path) as f:
        for i in range(10):
            line = f.next()
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

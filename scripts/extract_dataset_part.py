"""
Reads a JSON file and uses it to call into a datatype class to extract
a subset of a dataset for processing.

Used by jobs that split large files into pieces to be processed concurrently
on a gid in a scatter-gather mode. This does part of the scatter.

"""

import json
import logging
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

# This junk is here to prevent loading errors
import galaxy.model.mapping  # need to load this before we unpickle, in order to setup properties assigned by the mappers

galaxy.model.Job()  # this looks REAL stupid, but it is REQUIRED in order for SA to insert parameters into the classes defined by the mappers --> it appears that instantiating ANY mapper'ed class would suffice here

logging.basicConfig()
log = logging.getLogger(__name__)


def __main__():
    """
    Argument: a JSON file
    """
    file_path = sys.argv.pop(1)
    if not os.path.isfile(file_path):
        # Nothing to do - some splitters don't write a JSON file
        sys.exit(0)
    data = json.load(open(file_path))
    try:
        class_name_parts = data["class_name"].split(".")
        module_name = ".".join(class_name_parts[:-1])
        class_name = class_name_parts[-1]
        mod = __import__(module_name, globals(), locals(), [class_name])
        cls = getattr(mod, class_name)
        if not cls.process_split_file(data):
            sys.stderr.write("Writing split file failed\n")
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit(1)


__main__()

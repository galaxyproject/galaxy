import os
import re

LIST_SEP = re.compile("\s*,\s*")


class TestDataResolver(object):

    def __init__(self, env_var, environ=os.environ):
        file_dirs = environ.get(env_var, None)
        if file_dirs:
            self.file_dirs = LIST_SEP.split(file_dirs)
        else:
            self.file_dirs = []

    def get_filename(self, name):
        if not self.file_dirs:
            filename = None
        else:
            filename = os.path.join(self.file_dirs[0], name)
            # For backward compat. returning first path if none
            # exist - though I don't know if this function is ever
            # actually used in a context where one should return
            # a file even if it doesn't exist (e.g. a prefix or
            # or something) - I am pretty sure it is not used in
            # such a fashion in the context of tool tests.
            if not os.path.exists(filename):
                for file_dir in self.file_dirs[1:]:
                    query_filename = os.path.join(file_dir, name)
                    if os.path.exists(query_filename):
                        filename = query_filename
        return os.path.abspath(filename)

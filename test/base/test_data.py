import os
import re

LIST_SEP = re.compile("\s*,\s*")


class TestDataResolver(object):

    def __init__(self, env_var, environ=os.environ):
        file_dirs = environ.get(env_var, None)
        if file_dirs:
            self.resolvers = map(FileDataResolver, LIST_SEP.split(file_dirs))
        else:
            self.resolvers = []

    def get_filename(self, name):
        if not self.resolvers:
            filename = None
        else:
            resolver = self.resolvers[0]
            filename = resolver.path(name)
            if not resolver.exists(filename):
                for resolver in self.resolvers[1:]:
                    if resolver.exists(name):
                        filename = resolver.path(name)
            else:
                # For backward compat. returning first path if none
                # exist - though I don't know if this function is ever
                # actually used in a context where one should return
                # a file even if it doesn't exist (e.g. a prefix or
                # or something) - I am pretty sure it is not used in
                # such a fashion in the context of tool tests.
                filename = resolver.path(name)
        return os.path.abspath(filename)


class FileDataResolver(object):

    def __init__(self, file_dir):
        self.file_dir = file_dir

    def exists(self, filename):
        return os.path.exists(self.path(filename))

    def path(self, filename):
        return os.path.join(self.file_dir, filename)

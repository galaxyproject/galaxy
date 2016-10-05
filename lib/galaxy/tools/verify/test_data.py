from __future__ import print_function

import hashlib
import os
import re
import subprocess

from string import Template

from galaxy.util import asbool

UPDATE_TEMPLATE = Template(
    "git --work-tree $dir --git-dir $dir/.git fetch && "
    "git --work-tree $dir --git-dir $dir/.git merge origin/master"
)

UPDATE_FAILED_TEMPLATE = Template(
    "Warning failed to update test repository $dir - "
    "update stdout was [$stdout] and stderr was [$stderr]."
)


LIST_SEP = re.compile("\s*,\s*")


class TestDataResolver(object):

    def __init__(self, env_var='GALAXY_TEST_FILE_DIR', environ=os.environ):
        file_dirs = environ.get(env_var, None)
        if file_dirs:
            self.resolvers = map(lambda u: build_resolver(u, environ), LIST_SEP.split(file_dirs))
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


def build_resolver(uri, environ):
    if uri.startswith("http") and uri.endswith(".git"):
        return GitDataResolver(uri, environ)
    else:
        return FileDataResolver(uri)


class FileDataResolver(object):

    def __init__(self, file_dir):
        self.file_dir = file_dir

    def exists(self, filename):
        return os.path.exists(self.path(filename))

    def path(self, filename):
        return os.path.join(self.file_dir, filename)


class GitDataResolver(FileDataResolver):

    def __init__(self, repository, environ):
        self.repository = repository
        self.updated = False
        repo_cache = environ.get("GALAXY_TEST_DATA_REPO_CACHE", "test-data-cache")
        m = hashlib.md5()
        m.update(repository)
        repo_path = os.path.join(repo_cache, m.hexdigest())
        super(GitDataResolver, self).__init__(repo_path)
        # My preference would be for this to be false, but for backward compat
        # will leave it as true for now.
        self.fetch_data = asbool(environ.get("GALAXY_TEST_FETCH_DATA", "true"))

    def exists(self, filename):
        exists_now = super(GitDataResolver, self).exists(filename)
        if exists_now or not self.fetch_data or self.updated:
            return exists_now
        self.update_repository()
        return super(GitDataResolver, self).exists(filename)

    def update_repository(self):
        self.updated = True
        if not os.path.exists(self.file_dir):
            parent_dir = os.path.dirname(self.file_dir)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            self.execute("git clone '%s' '%s'" % (self.repository, self.file_dir))
        update_command = UPDATE_TEMPLATE.safe_substitute(dir=self.file_dir)
        self.execute(update_command)

    def execute(self, cmd):
        subprocess_kwds = dict(
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print("Executing %s" % cmd)
        p = subprocess.Popen(cmd, **subprocess_kwds)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            kwds = {
                'dir': self.file_dir,
                'stdout': stdout,
                'stderr': stderr,
            }
            print(UPDATE_FAILED_TEMPLATE.substitute(**kwds))

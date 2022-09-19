import hashlib
import os
import re
import subprocess
from string import Template

from galaxy.util import (
    asbool,
    in_directory,
    smart_str,
)

UPDATE_TEMPLATE = Template(
    "git --work-tree $dir --git-dir $dir/.git fetch && " "git --work-tree $dir --git-dir $dir/.git merge origin/master"
)

UPDATE_FAILED_TEMPLATE = Template(
    "Warning failed to update test repository $dir - " "update stdout was [$stdout] and stderr was [$stderr]."
)


LIST_SEP = re.compile(r"\s*,\s*")


class TestDataResolver:
    __test__ = False  # Prevent pytest from discovering this class (issue #12071)

    def __init__(self, file_dirs=None, env_var="GALAXY_TEST_FILE_DIR", environ=os.environ):
        if file_dirs is None:
            file_dirs = environ.get(env_var, None)
        if file_dirs is None:
            file_dirs = "test-data,https://github.com/galaxyproject/galaxy-test-data.git"
        if file_dirs:
            self.resolvers = [build_resolver(u, environ) for u in LIST_SEP.split(file_dirs)]
        else:
            self.resolvers = []

    def get_filename(self, name):
        for resolver in self.resolvers or []:
            if not resolver.exists(name):
                continue
            filename = resolver.path(name)
            if filename:
                return os.path.abspath(filename)

    def get_filecontent(self, name):
        filename = self.get_filename(name=name)
        with open(filename, mode="rb") as f:
            return f.read()

    def get_directory(self, name):
        return self.get_filename(name=name)


def build_resolver(uri, environ):
    if uri.startswith("http") and uri.endswith(".git"):
        return GitDataResolver(uri, environ)
    else:
        return FileDataResolver(uri)


class FileDataResolver:
    def __init__(self, file_dir):
        self.file_dir = file_dir

    def exists(self, filename):
        path = os.path.abspath(self.path(filename))
        return os.path.exists(path) and in_directory(path, self.file_dir)

    def path(self, filename):
        return os.path.join(self.file_dir, filename)


class GitDataResolver(FileDataResolver):
    def __init__(self, repository, environ):
        self.repository = repository
        self.updated = False
        repo_cache = environ.get("GALAXY_TEST_DATA_REPO_CACHE", "test-data-cache")
        m = hashlib.md5()
        m.update(smart_str(repository))
        repo_path = os.path.join(repo_cache, m.hexdigest())
        super().__init__(repo_path)
        # My preference would be for this to be false, but for backward compat
        # will leave it as true for now.
        self.fetch_data = asbool(environ.get("GALAXY_TEST_FETCH_DATA", "true"))

    def exists(self, filename):
        exists_now = super().exists(filename)
        if exists_now or not self.fetch_data or self.updated:
            return exists_now
        self.update_repository()
        return super().exists(filename)

    def update_repository(self):
        self.updated = True
        if not os.path.exists(self.file_dir):
            parent_dir = os.path.dirname(self.file_dir)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            self.execute(f"git clone '{self.repository}' '{self.file_dir}'")
        update_command = UPDATE_TEMPLATE.safe_substitute(dir=self.file_dir)
        self.execute(update_command)

    def execute(self, cmd):
        subprocess_kwds = dict(
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print(f"Executing {cmd}")
        p = subprocess.Popen(cmd, **subprocess_kwds)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            kwds = {
                "dir": self.file_dir,
                "stdout": stdout,
                "stderr": stderr,
            }
            print(UPDATE_FAILED_TEMPLATE.substitute(**kwds))

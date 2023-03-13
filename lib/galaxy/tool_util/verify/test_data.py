import hashlib
import os
import re
import subprocess
from string import Template
from typing import (
    Any,
    Dict,
    Optional,
)

from typing_extensions import Protocol

from galaxy.util import (
    asbool,
    download_to_file,
    in_directory,
    is_url,
    smart_str,
)
from galaxy.util.hash_util import (
    memory_bound_hexdigest,
    parse_checksum_hash,
)

UPDATE_TEMPLATE = Template(
    "git --work-tree $dir --git-dir $dir/.git fetch && " "git --work-tree $dir --git-dir $dir/.git merge origin/master"
)

UPDATE_FAILED_TEMPLATE = Template(
    "Warning failed to update test repository $dir - " "update stdout was [$stdout] and stderr was [$stderr]."
)


LIST_SEP = re.compile(r"\s*,\s*")

TestDataContext = Dict[str, Any]


class TestDataResolver:
    __test__ = False  # Prevent pytest from discovering this class (issue #12071)

    def __init__(self, file_dirs=None, env_var="GALAXY_TEST_FILE_DIR", environ=os.environ):
        if file_dirs is None:
            file_dirs = environ.get(env_var, None)
        if file_dirs is None:
            file_dirs = "test-data,url-location,https://github.com/galaxyproject/galaxy-test-data.git"
        if file_dirs:
            self.resolvers = [build_resolver(u, environ) for u in LIST_SEP.split(file_dirs)]
        else:
            self.resolvers = []

    def get_filename(self, name: str, context: Optional[TestDataContext] = None) -> str:
        for resolver in self.resolvers or []:
            if not resolver.exists(name, context):
                continue
            filename = resolver.path(name)
            if filename:
                return os.path.abspath(filename)
        raise TestDataNotFoundError(f"Failed to find test file {name} against any test data resolvers")

    def get_filecontent(self, name: str, context: Optional[TestDataContext] = None) -> bytes:
        filename = self.get_filename(name=name, context=context)
        with open(filename, mode="rb") as f:
            return f.read()

    def get_directory(self, name: str) -> str:
        return self.get_filename(name=name)


class TestDataNotFoundError(ValueError):
    pass


class TestDataChecksumError(ValueError):
    pass


def build_resolver(uri: str, environ):
    if uri.startswith("http") and uri.endswith(".git"):
        return GitDataResolver(uri, environ)
    elif uri == "url-location":
        return RemoteLocationDataResolver(environ)
    else:
        return FileDataResolver(uri)


class DataResolver(Protocol):
    def exists(self, filename: str, context: Optional[TestDataContext] = None):
        raise NotImplementedError

    def path(self, filename: str):
        raise NotImplementedError


class FileDataResolver(DataResolver):
    def __init__(self, file_dir: str):
        self.file_dir = file_dir

    def exists(self, filename: str, context: Optional[TestDataContext] = None):
        path = os.path.abspath(self.path(filename))
        return os.path.exists(path) and in_directory(path, self.file_dir)

    def path(self, filename: str):
        return os.path.join(self.file_dir, filename)


class GitDataResolver(FileDataResolver):
    def __init__(self, repository: str, environ):
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

    def exists(self, filename: str, context: Optional[TestDataContext] = None):
        exists_now = super().exists(filename, context)
        if exists_now or not self.fetch_data or self.updated:
            return exists_now
        self.update_repository()
        return super().exists(filename, context)

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


class RemoteLocationDataResolver(FileDataResolver):
    def __init__(self, environ):
        self.fetch_data = asbool(environ.get("GALAXY_TEST_FETCH_DATA", True))
        repo_cache = environ.get("GALAXY_TEST_DATA_REPO_CACHE", "test-data-cache")
        repo_path = os.path.join(repo_cache, "from-location")
        super().__init__(repo_path)

    def exists(self, filename: str, context: Optional[TestDataContext] = None):
        exists_now = super().exists(filename, context)
        if exists_now or not self.fetch_data or context is None:
            return exists_now
        self._try_download_from_location(filename, context)
        exists_now = super().exists(filename, context)
        if exists_now:
            self._verify_checksum(filename, context)
        return exists_now

    def _try_download_from_location(self, filename: str, context: TestDataContext):
        location = context.get("location")
        if location is None:
            return
        if not is_url(location):
            raise ValueError(f"Invalid 'location' URL for remote test data provided: {location}")
        if not self._is_valid_filename(filename):
            raise ValueError(f"Invalid 'filename' provided: '{filename}'")
        self._ensure_base_dir_exists()
        dest_file_path = self.path(filename)
        download_to_file(location, dest_file_path)

    def _ensure_base_dir_exists(self):
        if not os.path.exists(self.file_dir):
            os.makedirs(self.file_dir)

    def _verify_checksum(self, filename: str, context: Optional[TestDataContext] = None):
        if context is None or is_url(filename):
            return
        checksum = context.get("checksum")
        if checksum is None:
            return
        hash_function, expected_hash_value = parse_checksum_hash(checksum)
        file_path = self.path(filename)
        calculated_hash_value = memory_bound_hexdigest(hash_func_name=hash_function, path=file_path)
        if calculated_hash_value != expected_hash_value:
            raise TestDataChecksumError(
                f"Failed to validate test data '{filename}' with [{hash_function}] - expected [{expected_hash_value}] got [{calculated_hash_value}]"
            )

    def _is_valid_filename(self, filename: str):
        """
        Checks that the filename does not contain the following
        characters: <, >, :, ", /, \\, |, ?, *, or any control characters.
        """
        pattern = r"^[^<>:\"/\\|?*\x00-\x1F]+$"
        return bool(re.match(pattern, filename))

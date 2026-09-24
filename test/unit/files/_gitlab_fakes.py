"""Shared fakes for the GitLab and ARC file source tests.

Both plugins wrap ``arcfs.fs.GitLabARCFileSystem`` from the optional ``arcfs-fsspec`` package.
These helpers replace it with an in-memory fake so the tests run without the package and without
network access. ``install_fake`` takes the module and class to patch, because each plugin reads
the filesystem class from its own module.
"""

from aiohttp import (
    ClientResponseError,
    RequestInfo,
)
from multidict import (
    CIMultiDict,
    CIMultiDictProxy,
)
from yarl import URL

FAKE_TREE = {
    "": [
        {"name": "group/repo1:-:", "type": "directory"},
        {"name": "group/sub/repo2:-:", "type": "directory"},
        {"name": "other/repo3:-:", "type": "directory"},
    ],
    "group/repo1:-:": [
        {"name": "group/repo1:-:README.md", "type": "file"},
        {"name": "group/repo1:-:assays", "type": "directory"},
    ],
    "group/repo1:-:assays": [
        {"name": "group/repo1:-:assays/measurements.csv", "type": "file"},
    ],
}
FAKE_FILES = {
    "group/repo1:-:README.md": "hello from repo1\n",
    "group/repo1:-:assays/measurements.csv": "a,b\n1,2\n",
}
# A catalogue larger than a single GitLab page, to exercise multi-page assembly.
LARGE_TREE = {"": [{"name": f"group/repo{i:03d}:-:", "type": "directory"} for i in range(250)]}
# Larger than MAX_ITEMS_LIMIT, so windows beyond that bound can be exercised.
HUGE_TREE = {"": [{"name": f"group/repo{i:04d}:-:", "type": "directory"} for i in range(1500)]}


class FakeRecorder:
    def __init__(self):
        self.init_kwargs: list[dict] = []
        self.ls_calls: list[str] = []
        self.ls_error_for: dict[str, Exception] = {}
        self.list_page_calls: list[dict] = []
        self.walk_calls: list[str] = []
        self.get_file_calls: list[tuple[str, str]] = []
        self.put_file_calls: list[tuple[str, str]] = []
        self.closed = 0
        self.list_page_error: Exception | None = None
        self.list_page_membership: list = []
        self.put_file_error: Exception | None = None


def _make_fake_fs_class(recorder: FakeRecorder, tree: dict, files: dict):
    class FakeGitLabARCFileSystem:
        """Minimal stand-in for ``arcfs.fs.GitLabARCFileSystem``."""

        def __init__(self, **kwargs):
            recorder.init_kwargs.append(dict(kwargs))

        @staticmethod
        def _key(path: str) -> str:
            return (path or "").strip().strip("/")

        def ls(self, path, detail=True, **kwargs):
            key = self._key(path)
            recorder.ls_calls.append(key)
            if key in recorder.ls_error_for:
                raise recorder.ls_error_for[key]
            entries = tree.get(key, [])
            return entries if detail else [e["name"] for e in entries]

        def list_page(self, path, detail=True, *, offset=0, limit=50, **kwargs):
            key = self._key(path)
            recorder.list_page_calls.append({"path": key, "offset": offset, "limit": limit})
            recorder.list_page_membership.append(kwargs.get("membership"))
            if recorder.list_page_error is not None:
                raise recorder.list_page_error
            entries = tree.get(key, [])
            # Since 0.1.11 arcfs serves any window from the pages that cover it, so the fake
            # simply slices; no offset is special.
            return entries[offset : offset + limit], len(entries)

        def walk(self, path, detail=True, **kwargs):
            # fsspec's walk descends into every subdirectory, so the fake has to as well.
            pending = [self._key(path)]
            while pending:
                key = pending.pop(0)
                recorder.walk_calls.append(key)
                entries = tree.get(key, [])
                dirs = {e["name"]: e for e in entries if e["type"] == "directory"}
                found = {e["name"]: e for e in entries if e["type"] == "file"}
                yield key, dirs, found
                pending.extend(dirs)

        def get_file(self, rpath, lpath, **kwargs):
            key = self._key(rpath)
            recorder.get_file_calls.append((key, lpath))
            with open(lpath, "w") as f:
                f.write(files[key])

        def put_file(self, lpath, rpath, **kwargs):
            if recorder.put_file_error is not None:
                raise recorder.put_file_error
            recorder.put_file_calls.append((lpath, self._key(rpath)))

        def close(self):
            recorder.closed += 1

    return FakeGitLabARCFileSystem


def _is_sub_path(origin: str, destination: str) -> bool:
    """Mirror the client's ``isSubPath`` (client/src/components/FilesDialog/utilities.ts).

    The file dialog decides which entries belong to a directory with this comparison, so an ARC's
    entries have to satisfy it for recursive selection to behave.
    """

    def with_trailing_slash(path: str) -> str:
        return path if path.endswith("/") else f"{path}/"

    origin, destination = with_trailing_slash(origin), with_trailing_slash(destination)
    return origin != destination and destination.startswith(origin)


def install_fake(monkeypatch, module, source_class, tree: dict, files: dict) -> FakeRecorder:
    """Patch the filesystem class a plugin opens, and return the call recorder.

    ``_open_fs`` instantiates ``self.required_module``, so setting it on the plugin class is what
    redirects the source at the fake. It is also what ``FsspecFilesSource.__init__`` checks before
    it will construct the plugin at all.
    """
    recorder = FakeRecorder()
    monkeypatch.setattr(source_class, "required_module", _make_fake_fs_class(recorder, tree, files))
    return recorder


def response_error(status: int, message: str) -> ClientResponseError:
    """Build the error aiohttp raises for a non-2xx GitLab response."""
    url = URL("https://gitlab.example.org/api/v4/projects")
    headers: CIMultiDictProxy[str] = CIMultiDictProxy(CIMultiDict())
    request_info = RequestInfo(url=url, method="GET", headers=headers, real_url=url)
    return ClientResponseError(request_info, (), status=status, message=message)

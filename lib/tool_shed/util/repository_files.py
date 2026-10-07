"""Read file listings and contents for a repository revision straight from the hg revlog.

Paths are only ever looked up in the revision's manifest, never joined onto the
filesystem, so nothing outside the committed tree can be reached.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from galaxy.util import is_binary
from tool_shed.util.hg_util import file_size
from tool_shed_client.schema import (
    RepositoryFileContents,
    RepositoryFileEntry,
    RepositoryFileType,
)

if TYPE_CHECKING:
    from mercurial.context import changectx

MAX_CONTENT_BYTES = 1024 * 1024
# Part of every validator; bump it when what the listing or contents report changes.
FORMAT_VERSION = 1

SYMLINK_FLAG = b"l"
EXECUTABLE_FLAG = b"x"


def _file_type(flags: bytes) -> RepositoryFileType:
    return "symlink" if SYMLINK_FLAG in flags else "file"


def list_manifest(ctx: "changectx") -> list[RepositoryFileEntry]:
    manifest = ctx.manifest()
    entries = []
    for path in sorted(manifest):
        flags = manifest.flags(path)
        entries.append(
            RepositoryFileEntry(
                path=path.decode("utf-8", errors="replace"),
                size=file_size(ctx[path]),
                type=_file_type(flags),
                executable=EXECUTABLE_FLAG in flags,
            )
        )
    return entries


def listing_validator(ctx: "changectx") -> str:
    """Return a string that changes whenever list_manifest(ctx) could."""
    return f"files:{FORMAT_VERSION}:{ctx.hex().decode()}"


@dataclass(frozen=True)
class ManifestFile:
    ctx: "changectx"
    path: str
    flags: bytes
    filenode: bytes

    def validator(self, max_bytes: int = MAX_CONTENT_BYTES) -> str:
        """Return a string that changes whenever read_file(self, max_bytes) could, without reading the file."""
        return f"contents:{FORMAT_VERSION}:{max_bytes}:{self.filenode.hex()}:{self.flags.decode()}:{self.path}"


def find_manifest_file(ctx: "changectx", path: str) -> ManifestFile | None:
    """Look path up in the revision's manifest, or return None if it has no such file."""
    manifest = ctx.manifest()
    hg_path = path.encode("utf-8")
    # The C manifest compares NUL-terminated paths, so "a\0junk" would match "a".
    if b"\0" in hg_path or hg_path not in manifest:
        return None
    return ManifestFile(ctx=ctx, path=path, flags=manifest.flags(hg_path), filenode=manifest[hg_path])


def read_file(manifest_file: ManifestFile, max_bytes: int = MAX_CONTENT_BYTES) -> RepositoryFileContents:
    file_type = _file_type(manifest_file.flags)
    fctx = manifest_file.ctx[manifest_file.path.encode("utf-8")]
    size = file_size(fctx)
    contents = RepositoryFileContents(path=manifest_file.path, size=size, type=file_type, binary=False, truncated=False)
    if file_type == "symlink":
        return contents
    if size > max_bytes:
        contents.truncated = True
        return contents
    data = fctx.data()
    # The index size counts any copy metadata header; the data read here does not.
    contents.size = len(data)
    if is_binary(data):
        contents.binary = True
    else:
        contents.content = data.decode("utf-8", errors="replace")
    return contents

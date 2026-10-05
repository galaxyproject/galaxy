"""Crypt4GH wrapper datatype for Galaxy.

This module defines the :class:`Crypt4GH` datatype and the
:func:`build_crypt4gh_datatype` factory used by the registry to
dynamically create ``inner_ext.c4gh`` wrapper datatypes.

Design principles
-----------------
* The datatype **never** decrypts or inspects plaintext payload data.
* ``set_meta`` reads only the public Crypt4GH header and stores it
  Base64-encoded, along with the inferred inner extension.
* Typed wrappers (``<inner_ext>.c4gh``) match tool inputs accepting the
  inner format; decryption for such inputs happens on the compute side.
* Authorization to compute on the data is *not* datatype metadata. It is
  server-managed state and never travels with the dataset.
"""

import base64
import logging
import os
from inspect import isclass
from typing import (
    Any,
    TYPE_CHECKING,
)

from galaxy.datatypes.binary import Binary
from galaxy.datatypes.data import Data
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.objectstore import ObjectStoreAuth
from galaxy.util.crypt4gh import (
    check_crypt4gh,
    CRYPT4GH_FILE_EXT,
    is_crypt4gh_file_ext,
    read_crypt4gh_header,
    unwrap_crypt4gh_file_ext,
    wrap_crypt4gh_file_ext,
)

if TYPE_CHECKING:
    from galaxy.webapps.base.webapp import GalaxyWebTransaction

log = logging.getLogger(__name__)


class Crypt4GH(Binary):
    """Generic Crypt4GH wrapper datatype (``c4gh`` extension).

    Typed wrappers (e.g. ``fastqsanger.c4gh``) are created dynamically
    by :func:`build_crypt4gh_datatype` and carry a reference to their
    inner datatype instance for transparent matching.
    """

    file_ext = CRYPT4GH_FILE_EXT
    display_behavior = "download"

    # Set only on typed wrappers created by build_crypt4gh_datatype.
    crypt4gh_inner_datatype: Data | None = None

    # --- Metadata elements --------------------------------------------------

    MetadataElement(
        name="crypt4gh_header",
        default="",
        desc="Crypt4GH header (Base64-encoded)",
        readonly=True,
        visible=True,
        optional=False,
        no_value="",
    )

    MetadataElement(
        name="crypt4gh_inner_ext",
        default="data",
        desc="Wrapped datatype extension",
        readonly=True,
        visible=True,
        optional=True,
        no_value="data",
    )

    # --- Sniffing -----------------------------------------------------------

    def sniff(self, filename: str) -> bool:
        """Return True if *filename* is a Crypt4GH file belonging to this datatype.

        For the generic ``c4gh`` wrapper, the magic-byte header check is
        sufficient.  For typed wrappers (e.g. ``fastqsanger.c4gh``), the
        original filename must also end with the expected inner extension
        so that a generic file is not mis-attributed to a specific type.
        """
        if not check_crypt4gh(filename):
            return False
        if self.file_ext == CRYPT4GH_FILE_EXT:
            return True
        basename = os.path.basename(filename)
        unwrapped_name = unwrap_crypt4gh_file_ext(basename)
        if unwrapped_name is None:
            return False
        inner_ext = unwrap_crypt4gh_file_ext(self.file_ext)
        return inner_ext is not None and unwrapped_name.endswith(f".{inner_ext}")

    # --- Metadata -----------------------------------------------------------

    def set_meta(
        self,
        dataset: DatasetProtocol,
        overwrite: bool = True,
        **kwd: Any,
    ) -> None:
        """Read the public Crypt4GH header and store metadata.

        This method **never** reads or decrypts payload data.  It only
        parses the header portion of the file.
        """
        header = read_crypt4gh_header(dataset.get_file_name())
        # Always describe the file itself, metadata copied from another dataset (e.g. a tool input) is wrong here.
        dataset.metadata.crypt4gh_header = base64.b64encode(header).decode("ascii")
        dataset.metadata.crypt4gh_inner_ext = self._infer_inner_ext(dataset)

    def set_peek(self, dataset: DatasetProtocol, **kwd: Any) -> None:
        if not dataset.dataset.purged:
            dataset.peek = f"Encrypted Crypt4GH dataset wrapping '{self._infer_inner_ext(dataset)}'"
            dataset.blurb = "encrypted"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        return dataset.peek or "Encrypted Crypt4GH dataset"

    # --- Matching -----------------------------------------------------------

    def matches_any(self, target_datatypes: list[Any]) -> bool:
        """Check if this datatype matches any of *target_datatypes*.

        Typed wrappers also match tool inputs that accept their inner
        format, the generic ``c4gh`` wrapper only matches directly.
        """
        datatype_classes = tuple(datatype if isclass(datatype) else datatype.__class__ for datatype in target_datatypes)
        if datatype_classes and isinstance(self, datatype_classes):
            return True
        inner_datatype = self.crypt4gh_inner_datatype
        if inner_datatype is not None:
            return inner_datatype.matches_any(target_datatypes)
        return False

    # --- Download / archive -------------------------------------------------

    def is_archive_download(self, datatypes_registry: Any, extension: str) -> bool:
        """Return ``True`` so downloads go through :meth:`_serve_file_download`.

        Crypt4GH datasets may have encrypted extra files that must be
        included in a zip archive.  Since :meth:`is_archive_download`
        cannot inspect the dataset instance, :meth:`_serve_file_download`
        decides whether to zip (extra files present) or serve the primary
        file directly.
        """
        return True

    def _serve_file_download(
        self,
        headers: Any,
        data: Any,
        trans: "GalaxyWebTransaction",
        to_ext: str | None,
        file_size: int,
        **kwd: Any,
    ) -> Any:
        """Serve a Crypt4GH dataset download.

        If the dataset has extra files, produce a zip archive containing
        the primary encrypted file and all encrypted extra files.
        Otherwise, serve the primary file directly as a regular download.
        """
        if self._has_extra_files(data):
            return self._archive_composite_dataset(trans, data, headers, do_action=kwd.get("do_action", "zip"))
        # No extra files — serve the primary file directly.
        headers["Content-Length"] = str(file_size)
        headers["content-type"] = "application/octet-stream"
        headers["Content-Disposition"] = self.content_disposition(data, to_ext, **kwd)

        return open(data.get_file_name(auth=ObjectStoreAuth(user=trans.user)), "rb"), headers

    def _archive_main_file(self, archive: Any, display_name: str, data_filename: str) -> tuple[bool, str, str]:
        """Add the primary Crypt4GH file to the download archive.

        Unlike the default implementation which writes the file as
        ``{display_name}.html``, this writes it with its actual encrypted
        extension (e.g. ``fastqsanger.c4gh``).
        """
        error, msg, messagetype = False, "", ""
        archname = f"{display_name}.{self.file_ext}"
        try:
            archive.write(data_filename, archname)
        except OSError:
            error = True
            log.exception("Unable to add Crypt4GH primary file %s to download archive", data_filename)
            msg = "Unable to create archive for download, please report this error"
            messagetype = "error"
        return error, msg, messagetype

    def _has_extra_files(self, dataset: Any) -> bool:
        """Check if *dataset* has a non-empty extra files directory."""
        extra_files_path = getattr(dataset, "extra_files_path", None)
        if not extra_files_path or not os.path.isdir(extra_files_path):
            return False
        for _root, _dirs, files in os.walk(extra_files_path):
            if files:
                return True
        return False

    # --- Internal helpers ---------------------------------------------------

    def _infer_inner_ext(self, dataset: DatasetProtocol) -> str:
        # 1. Typed wrapper extension (e.g. fastqsanger.c4gh -> fastqsanger)
        dataset_ext = unwrap_crypt4gh_file_ext(self.file_ext)
        if dataset_ext is not None:
            return dataset_ext
        # 2. Dataset's own extension
        dataset_ext = unwrap_crypt4gh_file_ext(dataset.extension)
        if dataset_ext is not None:
            return dataset_ext
        # 3. Original upload filename
        created_from_basename = getattr(dataset.dataset, "created_from_basename", None)
        if created_from_basename:
            unwrapped_name = unwrap_crypt4gh_file_ext(created_from_basename)
            if unwrapped_name is not None:
                return unwrapped_name.rsplit(".", 1)[-1]
        return "data"


def build_crypt4gh_datatype(inner_datatype: Data) -> Crypt4GH:
    """Create a typed Crypt4GH wrapper datatype instance for *inner_datatype*.

    The resulting class inherits from :class:`Crypt4GH` and carries the
    inner datatype instance as ``crypt4gh_inner_datatype`` so that
    ``matches_any`` can delegate to it.
    """
    datatype_class = type(
        f"{inner_datatype.__class__.__name__}Crypt4gh",
        (Crypt4GH,),
        {
            "file_ext": f"{inner_datatype.file_ext}.{CRYPT4GH_FILE_EXT}",
            "crypt4gh_inner_datatype": inner_datatype,
            "edam_format": getattr(inner_datatype, "edam_format", Crypt4GH.edam_format),
            "edam_data": getattr(inner_datatype, "edam_data", Crypt4GH.edam_data),
        },
    )
    wrapper: Crypt4GH = datatype_class()
    return wrapper


__all__ = (
    "CRYPT4GH_FILE_EXT",
    "Crypt4GH",
    "build_crypt4gh_datatype",
    "is_crypt4gh_file_ext",
    "unwrap_crypt4gh_file_ext",
    "wrap_crypt4gh_file_ext",
)

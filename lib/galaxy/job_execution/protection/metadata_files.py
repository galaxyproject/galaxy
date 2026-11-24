"""Create the metadata files of decrypted data (e.g. BAM indexes) on the compute host.

Encrypted datasets can't have the metadata files of their format created when they are stored: Galaxy only
sees the encrypted data. Jobs decrypting the data create them, encrypted for outputs, or for the job only
for inputs stored without them.
"""

import logging
import os
import shutil
import sys
from collections.abc import (
    Iterable,
    Iterator,
)
from contextlib import contextmanager
from typing import TYPE_CHECKING

from galaxy.datatypes.crypt4gh import metadata_file_names
from galaxy.datatypes.registry import Registry
from galaxy.model import (
    Dataset,
    HistoryDatasetAssociation,
    set_datatypes_registry,
)
from galaxy.model.metadata import MetadataTempFile

if TYPE_CHECKING:
    from galaxy.datatypes.data import Data

log = logging.getLogger(__name__)

# File descriptors of the standard output and error.
STANDARD_STREAMS = (1, 2)


def load_datatypes_registry(datatypes_config: str) -> Registry:
    """Load the datatypes Galaxy wrote for the job, and make dataset instances use them."""
    registry = Registry()
    registry.load_datatypes(
        # Only locates converters and display applications, which aren't loaded. Compute hosts may run
        # installed packages, without a Galaxy checkout to find.
        root_dir=os.path.dirname(os.path.abspath(datatypes_config)),
        config=datatypes_config,
        use_build_sites=False,
        use_converters=False,
        use_display_applications=False,
    )
    set_datatypes_registry(registry)
    return registry


def create_metadata_files(datatype: "Data", path: str, directory: str) -> dict[str, str]:
    """Create the metadata files ``datatype`` comes with for the decrypted file at ``path``, in ``directory``.

    Runs the datatype's own metadata step on a throwaway dataset and keeps only the files: the other
    metadata describes the decrypted content. Returns the paths of the files by metadata name, none when
    the datatype fails to create them: tools then go without them, as for datasets whose metadata failed.
    Needs the datatypes registry (``galaxy.model.set_datatypes_registry``).
    """
    names = metadata_file_names(datatype)
    if not names:
        return {}
    os.makedirs(directory, exist_ok=True)
    # Datatypes may write files next to the data, e.g. pysam compresses data it indexes with tabix that isn't
    # compressed yet. Reading the data through a link in ``directory`` keeps them there.
    data_link = os.path.join(directory, "data")
    os.symlink(os.path.abspath(path), data_link)
    dataset = Dataset(external_filename=data_link)
    # Datatypes not passing ``metadata_tmp_files_dir`` on (Tool Shed ones may not) create their files where
    # ``new_file`` says: in ``directory`` too, never unencrypted in the object store.
    dataset.object_store = None  # type: ignore[misc]
    dataset_instance = HistoryDatasetAssociation(extension=datatype.file_ext, dataset=dataset, flush=False)
    try:
        with _quiet(), _temp_files_in(directory):
            datatype.set_meta(dataset_instance, metadata_tmp_files_dir=directory)
        files: dict[str, str] = {}
        for name in names:
            value = dataset_instance.metadata.get(name)
            if isinstance(value, MetadataTempFile) and os.path.getsize(value.get_file_name()) > 0:
                files[name] = value.get_file_name()
    except Exception:
        # The error may quote the decrypted data.
        log.warning("Could not create the metadata files of a decrypted '%s' dataset.", datatype.file_ext)
        shutil.rmtree(directory, ignore_errors=True)
        return {}
    _remove_other_files(directory, files.values())
    return files


def _remove_other_files(directory: str, kept: Iterable[str]) -> None:
    """Remove everything in ``directory`` but the ``kept`` files, it may be derived from the decrypted data."""
    kept_names = {os.path.basename(path) for path in kept}
    for name in os.listdir(directory):
        if name in kept_names:
            continue
        path = os.path.join(directory, name)
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


@contextmanager
def _temp_files_in(directory: str) -> Iterator[None]:
    """Create the metadata temp files of datatypes not given a directory in ``directory``."""
    previous_tmp_dir = MetadataTempFile.tmp_dir
    MetadataTempFile.tmp_dir = directory
    try:
        yield
    finally:
        MetadataTempFile.tmp_dir = previous_tmp_dir


@contextmanager
def _quiet() -> Iterator[None]:
    """Keep what datatypes log or print out of the job's output, it may quote the decrypted data.

    Libraries like htslib write to the process's standard streams directly (e.g. the name of a read that
    can't be indexed), not all of it is captured into exceptions.
    """
    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    sys.stdout.flush()
    sys.stderr.flush()
    saved = {fd: os.dup(fd) for fd in STANDARD_STREAMS}
    try:
        with open(os.devnull, "w") as devnull:
            for fd in STANDARD_STREAMS:
                os.dup2(devnull.fileno(), fd)
        yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        for fd, saved_fd in saved.items():
            os.dup2(saved_fd, fd)
            os.close(saved_fd)
        logging.disable(previous_disable)

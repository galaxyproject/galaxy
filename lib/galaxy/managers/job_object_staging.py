"""Serve a running job's inputs to a remote job runner from the object store.

Galaxy gives a remote runner (Pulsar) one signed URL per input (``input_url``,
kept beside the code that verifies it) instead of a path on its own disk. A request for such a URL is answered from the
object store by identity (``staged_input``): with a redirect to a presigned URL
when the URL asks for one and the store can issue it, else with a stream read
straight from the store, else from a local file (disk stores).
Nothing here needs a filesystem shared between Galaxy hosts.
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import (
    Any,
    Literal,
)
from urllib.parse import quote

from sqlalchemy import (
    or_,
    Select,
    select,
)

from galaxy import exceptions
from galaxy.model import (
    Dataset,
    DatasetInstance,
    HistoryDatasetAssociation,
    Job,
    JobToInputDatasetAssociation,
    JobToInputLibraryDatasetAssociation,
    LibraryDatasetDatasetAssociation,
    MetadataFile,
)
from galaxy.model.metadata import FileParameter
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.objectstore import (
    BaseObjectStore,
    DataStream,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.security.staging_signer import StagingUrlSigner

log = logging.getLogger(__name__)

StagedInputKind = Literal["dataset", "metadata_file", "extra_file"]

# The staging URLs a runner receives must outlive the job's wait in a queue; the
# job leaving Job.non_ready_states ends them sooner.
INPUT_URL_LIFETIME_SECONDS = 7 * 24 * 60 * 60

# A presigned URL Galaxy redirects to outlives the job, as Galaxy cannot revoke it.
# The runner follows it at once and comes back to the staging URL to resume or
# retry, so it need only last one request, with a margin for clock skew between
# Galaxy and the store.
REDIRECT_URL_LIFETIME_SECONDS = 15 * 60


@dataclass
class StagedInput:
    """How to answer a staging request: exactly one of the transfer fields is set, none for HEAD."""

    size: int
    redirect_url: str | None = None
    stream: DataStream | None = None
    path: str | None = None


def input_url(
    security: IdEncodingHelper,
    galaxy_url: str,
    job_id: int,
    kind: StagedInputKind,
    object_id: int,
    expires: int,
    redirect: bool = False,
    path: str = "",
) -> str:
    """A signed URL for one input of a job, answered by ``JobObjectStagingManager.staged_input``.

    With ``redirect``, the runner may be sent to a presigned object store URL; only ask for that when
    the runner can reach the store and follows redirects. The flag is not signed: it only changes how
    the job receives its own input. An ``extra_file`` is the file at ``path`` among the extra files of
    dataset ``object_id``.
    """
    signature = StagingUrlSigner(security.id_secret).sign(job_id, kind, object_id, path, expires)
    encoded_job_id = security.encode_id(job_id)
    encoded_object_id = security.encode_id(object_id)
    url = (
        f"{galaxy_url}/api/jobs/{encoded_job_id}/staging/inputs/{kind}/{encoded_object_id}"
        f"?exp={expires}&sig={signature}"
    )
    if path:
        url = f"{url}&path={quote(path, safe='')}"
    return f"{url}&redirect=1" if redirect else url


class JobObjectStagingManager:
    def __init__(
        self, sa_session: galaxy_scoped_session, object_store: BaseObjectStore, security: IdEncodingHelper
    ) -> None:
        self._sa_session = sa_session
        self._object_store = object_store
        self._signer = StagingUrlSigner(security.id_secret)

    def staged_input(
        self,
        job_id: int,
        kind: StagedInputKind,
        object_id: int,
        expires: int,
        signature: str,
        head: bool = False,
        redirect: bool = False,
        path: str = "",
    ) -> StagedInput:
        if not self._signer.verify(job_id, kind, object_id, path, expires, signature):
            raise exceptions.ItemAccessibilityException("Invalid or expired staging URL.")
        job = self._sa_session.get(Job, job_id)
        if job is None or job.state not in Job.non_ready_states:
            raise exceptions.ItemAccessibilityException("Attempting to stage an input of a job that is not active.")
        obj, dataset, path_kwargs = self._input_object(job, kind, object_id, path)
        if dataset.purged:
            raise exceptions.ItemDeletionException("Input dataset(s) for job have been purged.")
        size = self._object_store.size(obj, **path_kwargs)
        # Stores report a missing object's size as 0, and presign or stream it as if it were empty.
        if size == 0 and not self._object_store.exists(obj, **path_kwargs):
            raise exceptions.ObjectNotFound(f"Requested {kind} is not in the object store.")
        if head:
            return StagedInput(size=size)
        if redirect and (
            redirect_url := self._object_store.get_direct_download_url(
                obj, expires_in=REDIRECT_URL_LIFETIME_SECONDS, **path_kwargs
            )
        ):
            return StagedInput(size=size, redirect_url=redirect_url)
        if (stream := self._object_store.get_data_stream(obj, write_cache=False, **path_kwargs)) is not None:
            return StagedInput(size=size, stream=stream)
        return StagedInput(size=size, path=self._object_store.get_filename(obj, **path_kwargs))

    def _input_object(
        self, job: Job, kind: StagedInputKind, object_id: int, path: str
    ) -> tuple[Dataset | MetadataFile, Dataset, dict[str, Any]]:
        """The object to read, the input dataset it belongs to, and where it sits in that dataset's store.

        Only the inputs the request is for are loaded: a job's inputs can number thousands, and each of
        their files is staged with its own request.
        """
        if kind in ("dataset", "extra_file"):
            history_datasets = select(HistoryDatasetAssociation.dataset_id).where(
                HistoryDatasetAssociation.id.in_(_history_input_ids(job.id))
            )
            library_datasets = select(LibraryDatasetDatasetAssociation.dataset_id).where(
                LibraryDatasetDatasetAssociation.id.in_(_library_input_ids(job.id))
            )
            stmt = select(Dataset).where(
                Dataset.id == object_id, or_(Dataset.id.in_(history_datasets), Dataset.id.in_(library_datasets))
            )
            if (dataset := self._sa_session.scalars(stmt).first()) is not None:
                path_kwargs = dataset.extra_file_object_store_path_kwargs(path) if kind == "extra_file" else {}
                return dataset, dataset, path_kwargs
        elif kind == "metadata_file" and (metadata_file := self._sa_session.get(MetadataFile, object_id)):
            for instance in self._inputs_with_metadata_file(job.id, metadata_file):
                if instance.dataset is not None and any(named.id == object_id for named in _metadata_files(instance)):
                    return metadata_file, instance.dataset, metadata_file.object_store_path_kwargs()
        raise exceptions.ItemAccessibilityException(f"Requested {kind} is not an input of this job.")

    def _inputs_with_metadata_file(
        self, job_id: int, metadata_file: MetadataFile
    ) -> list[HistoryDatasetAssociation | LibraryDatasetDatasetAssociation]:
        """The job's inputs that own ``metadata_file``, or a metadata file with its uuid.

        Metadata file uuids are not unique in existing databases (importing a history twice repeats them),
        and an input naming its file by uuid resolves to the oldest row with it, which may be another
        dataset's.
        """
        same_file = MetadataFile.id == metadata_file.id
        if metadata_file.uuid is not None:
            same_file = or_(same_file, MetadataFile.uuid == metadata_file.uuid)
        owners = select(MetadataFile.hda_id).where(same_file)
        library_owners = select(MetadataFile.lda_id).where(same_file)
        history_inputs = select(HistoryDatasetAssociation).where(
            HistoryDatasetAssociation.id.in_(owners),
            HistoryDatasetAssociation.id.in_(_history_input_ids(job_id)),
        )
        library_inputs = select(LibraryDatasetDatasetAssociation).where(
            LibraryDatasetDatasetAssociation.id.in_(library_owners),
            LibraryDatasetDatasetAssociation.id.in_(_library_input_ids(job_id)),
        )
        return [*self._sa_session.scalars(history_inputs), *self._sa_session.scalars(library_inputs)]


def _history_input_ids(job_id: int) -> Select[tuple[int | None]]:
    """Ids of the job's history dataset inputs."""
    return select(JobToInputDatasetAssociation.dataset_id).where(JobToInputDatasetAssociation.job_id == job_id)


def _library_input_ids(job_id: int) -> Select[tuple[int]]:
    """Ids of the job's library dataset inputs."""
    return select(JobToInputLibraryDatasetAssociation.ldda_id).where(
        JobToInputLibraryDatasetAssociation.job_id == job_id
    )


def _metadata_files(dataset_instance: DatasetInstance) -> Iterator[MetadataFile]:
    """The metadata files a dataset's metadata names, resolved as for a tool's command line."""
    for name, spec in dataset_instance.metadata.spec.items():
        if isinstance(spec.param, FileParameter):
            value = dataset_instance.metadata.get(name)
            if isinstance(value, MetadataFile):
                yield value

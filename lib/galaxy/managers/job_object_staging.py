"""Serve a running job's inputs to a remote job runner from the object store.

Galaxy gives a remote runner (Pulsar) one signed URL per input (``input_url``,
kept beside the code that verifies it) instead of a path on its own disk. A request for such a URL is answered from the
object store by identity (``staged_input``): with a redirect to a presigned URL
when the URL asks for one and the store can issue it, else with a stream read
straight from the store, else from a local file (disk stores).
Nothing here needs a filesystem shared between Galaxy hosts.
"""

import logging
from dataclasses import dataclass
from typing import (
    Any,
    Literal,
)

from galaxy import exceptions
from galaxy.model import (
    Dataset,
    Job,
    MetadataFile,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.objectstore import (
    BaseObjectStore,
    DataStream,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.security.staging_signer import StagingUrlSigner

log = logging.getLogger(__name__)

StagedInputKind = Literal["dataset", "metadata_file"]

# The staging URLs a runner receives must outlive the job's wait in a queue; the
# job leaving Job.non_ready_states ends them sooner.
INPUT_URL_LIFETIME_SECONDS = 7 * 24 * 60 * 60


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
) -> str:
    """A signed URL for one input of a job, answered by ``JobObjectStagingManager.staged_input``.

    With ``redirect``, the runner may be sent to a presigned object store URL; only ask for that when
    the runner can reach the store and follows redirects. The flag is not signed: it only changes how
    the job receives its own input.
    """
    signature = StagingUrlSigner(security.id_secret).sign(job_id, kind, object_id, "", expires)
    encoded_job_id = security.encode_id(job_id)
    encoded_object_id = security.encode_id(object_id)
    url = (
        f"{galaxy_url}/api/jobs/{encoded_job_id}/staging/inputs/{kind}/{encoded_object_id}"
        f"?exp={expires}&sig={signature}"
    )
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
    ) -> StagedInput:
        if not self._signer.verify(job_id, kind, object_id, "", expires, signature):
            raise exceptions.ItemAccessibilityException("Invalid or expired staging URL.")
        job = self._sa_session.get(Job, job_id)
        if job is None or job.state not in Job.non_ready_states:
            raise exceptions.ItemAccessibilityException("Attempting to stage an input of a job that is not active.")
        obj, dataset, path_kwargs = self._input_object(job, kind, object_id)
        if dataset.purged:
            raise exceptions.ItemDeletionException("Input dataset(s) for job have been purged.")

        size = self._object_store.size(obj, **path_kwargs)
        if head:
            return StagedInput(size=size)
        if redirect and (redirect_url := self._object_store.get_direct_download_url(obj, **path_kwargs)):
            return StagedInput(size=size, redirect_url=redirect_url)
        if (stream := self._object_store.get_data_stream(obj, write_cache=False, **path_kwargs)) is not None:
            return StagedInput(size=size, stream=stream)
        return StagedInput(size=size, path=self._object_store.get_filename(obj, **path_kwargs))

    def _input_object(
        self, job: Job, kind: StagedInputKind, object_id: int
    ) -> tuple[Dataset | MetadataFile, Dataset, dict[str, Any]]:
        """The object to read, the dataset it belongs to, and where it sits in that dataset's store."""
        input_associations = [
            *(assoc.dataset for assoc in job.input_datasets),
            *(assoc.dataset for assoc in job.input_library_datasets),
        ]
        if kind == "dataset":
            for association in input_associations:
                dataset = association.dataset if association is not None else None
                if dataset is not None and dataset.id == object_id:
                    return dataset, dataset, {}
        elif kind == "metadata_file":
            metadata_file = self._sa_session.get(MetadataFile, object_id)
            if metadata_file is not None:
                owner = metadata_file.history_dataset or metadata_file.library_dataset
                if owner is not None and owner.dataset is not None and owner in input_associations:
                    return metadata_file, owner.dataset, metadata_file.object_store_path_kwargs()
        raise exceptions.ItemAccessibilityException(f"Requested {kind} is not an input of this job.")

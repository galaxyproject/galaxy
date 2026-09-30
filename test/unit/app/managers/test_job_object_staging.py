import os
import time
from unittest import mock
from urllib.parse import (
    parse_qs,
    urlparse,
)

import pytest

from galaxy import exceptions
from galaxy.managers.job_object_staging import (
    input_url,
    JobObjectStagingManager,
)
from galaxy.model import (
    Dataset,
    HistoryDatasetAssociation,
    Job,
    MetadataFile,
)
from galaxy.model.unittest_utils import GalaxyDataTestApp

GALAXY_URL = "https://galaxy.test"
CONTENT = b"input content"
LATER = int(time.time()) + 3600


@pytest.fixture
def app():
    return GalaxyDataTestApp()


@pytest.fixture
def manager(app) -> JobObjectStagingManager:
    return JobObjectStagingManager(app.model.session, app.object_store, app.security)


def _stored_hda(app, content=CONTENT) -> HistoryDatasetAssociation:
    hda = HistoryDatasetAssociation(sa_session=app.model.session, create_dataset=True)
    app.model.session.add(hda)
    app.model.session.commit()
    _store(app, _dataset(hda), content)
    return hda


def _dataset(hda: HistoryDatasetAssociation) -> Dataset:
    assert hda.dataset is not None
    return hda.dataset


def _store(app, obj, content, **path_kwargs):
    source = os.path.join(app.config.new_file_path, "source")
    os.makedirs(app.config.new_file_path, exist_ok=True)
    with open(source, "wb") as f:
        f.write(content)
    app.object_store.update_from_file(obj, file_name=source, create=True, **path_kwargs)


def _running_job(app, *inputs) -> Job:
    job = Job()
    job.state = Job.states.RUNNING
    for i, hda in enumerate(inputs):
        job.add_input_dataset(f"input{i}", hda)
    app.model.session.add(job)
    app.model.session.commit()
    return job


def _signed(app, job, kind, object_id, expires=LATER, redirect=False):
    """What a runner's request carries, read back from the URL the manager issues."""
    url = urlparse(input_url(app.security, GALAXY_URL, job.id, kind, object_id, expires, redirect=redirect))
    query = parse_qs(url.query)
    return dict(
        job_id=job.id,
        kind=kind,
        object_id=object_id,
        expires=int(query["exp"][0]),
        signature=query["sig"][0],
        redirect=query.get("redirect") == ["1"],
    )


def test_input_url_addresses_the_staging_endpoint(app, manager):
    hda = _stored_hda(app)
    job = _running_job(app, hda)
    url = urlparse(input_url(app.security, GALAXY_URL, job.id, "dataset", _dataset(hda).id, LATER))
    encoded_job, encoded_dataset = app.security.encode_id(job.id), app.security.encode_id(_dataset(hda).id)
    assert url.path == f"/api/jobs/{encoded_job}/staging/inputs/dataset/{encoded_dataset}"


def test_input_on_a_disk_store_is_served_from_its_file(app, manager):
    hda = _stored_hda(app)
    job = _running_job(app, hda)
    staged = manager.staged_input(**_signed(app, job, "dataset", _dataset(hda).id))
    assert staged.redirect_url is None and staged.stream is None
    with open(staged.path, "rb") as f:
        assert f.read() == CONTENT
    assert staged.size == len(CONTENT)


def test_request_with_a_signature_for_another_object_is_refused(app, manager):
    hda, other = _stored_hda(app), _stored_hda(app)
    job = _running_job(app, hda, other)
    request = {**_signed(app, job, "dataset", _dataset(hda).id), "object_id": _dataset(other).id}
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.staged_input(**request)


def test_request_with_an_expired_signature_is_refused(app, manager):
    hda = _stored_hda(app)
    job = _running_job(app, hda)
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.staged_input(**_signed(app, job, "dataset", _dataset(hda).id, expires=int(time.time()) - 1))


def test_request_for_a_finished_job_is_refused(app, manager):
    hda = _stored_hda(app)
    job = _running_job(app, hda)
    request = _signed(app, job, "dataset", _dataset(hda).id)
    job.state = Job.states.OK
    app.model.session.commit()
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.staged_input(**request)


def test_object_that_is_not_an_input_of_the_job_is_refused(app, manager):
    hda, not_an_input = _stored_hda(app), _stored_hda(app)
    job = _running_job(app, hda)
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.staged_input(**_signed(app, job, "dataset", _dataset(not_an_input).id))


def test_purged_input_is_reported_as_purged(app, manager):
    hda = _stored_hda(app)
    job = _running_job(app, hda)
    _dataset(hda).purged = True
    app.model.session.commit()
    with pytest.raises(exceptions.ItemDeletionException):
        manager.staged_input(**_signed(app, job, "dataset", _dataset(hda).id))


def test_redirect_mode_answers_with_a_presigned_url(app, manager):
    hda = _stored_hda(app)
    job = _running_job(app, hda)
    with mock.patch.object(app.object_store, "get_direct_download_url", return_value="https://s3/signed") as presign:
        staged = manager.staged_input(**_signed(app, job, "dataset", _dataset(hda).id, redirect=True))
    assert staged.redirect_url == "https://s3/signed"
    assert presign.call_args.args[0] is _dataset(hda)


def test_redirect_mode_streams_when_the_store_cannot_presign(app, manager):
    hda = _stored_hda(app)
    job = _running_job(app, hda)
    chunks = iter([CONTENT])
    with (
        mock.patch.object(app.object_store, "get_direct_download_url", return_value=None),
        mock.patch.object(app.object_store, "get_data_stream", return_value=chunks) as stream,
    ):
        staged = manager.staged_input(**_signed(app, job, "dataset", _dataset(hda).id, redirect=True))
    assert staged.stream is chunks
    # A one-off staging read must not fill the web worker's cache.
    assert stream.call_args.kwargs["write_cache"] is False


def test_url_without_redirect_never_redirects(app, manager):
    hda = _stored_hda(app)
    job = _running_job(app, hda)
    with (
        mock.patch.object(app.object_store, "get_direct_download_url", return_value="https://s3/signed") as presign,
        mock.patch.object(app.object_store, "get_data_stream", return_value=iter([CONTENT])),
    ):
        staged = manager.staged_input(**_signed(app, job, "dataset", _dataset(hda).id))
    assert staged.redirect_url is None
    presign.assert_not_called()


def test_head_request_reports_size_without_opening_the_object(app, manager):
    hda = _stored_hda(app)
    job = _running_job(app, hda)
    with (
        mock.patch.object(app.object_store, "get_direct_download_url") as presign,
        mock.patch.object(app.object_store, "get_data_stream") as stream,
    ):
        staged = manager.staged_input(**_signed(app, job, "dataset", _dataset(hda).id, redirect=True), head=True)
    assert staged.size == len(CONTENT)
    assert staged.redirect_url is None and staged.stream is None and staged.path is None
    presign.assert_not_called()
    stream.assert_not_called()


def _stored_metadata_file(app, hda, content=b"bam index") -> MetadataFile:
    metadata_file = MetadataFile(dataset=hda, name="bam_index")
    app.model.session.add(metadata_file)
    app.model.session.commit()
    source = os.path.join(app.config.new_file_path, "metadata_source")
    with open(source, "wb") as f:
        f.write(content)
    metadata_file.update_from_file(source)
    return metadata_file


def test_input_metadata_file_is_served_from_its_path_within_the_dataset(app, manager):
    hda = _stored_hda(app)
    metadata_file = _stored_metadata_file(app, hda)
    job = _running_job(app, hda)
    staged = manager.staged_input(**_signed(app, job, "metadata_file", metadata_file.id))
    assert staged.path == metadata_file.get_file_name()
    with open(staged.path, "rb") as f:
        assert f.read() == b"bam index"


def test_input_metadata_file_is_presigned_at_its_path_within_the_dataset(app, manager):
    hda = _stored_hda(app)
    metadata_file = _stored_metadata_file(app, hda)
    job = _running_job(app, hda)
    with mock.patch.object(app.object_store, "get_direct_download_url", return_value="https://s3/meta") as presign:
        staged = manager.staged_input(**_signed(app, job, "metadata_file", metadata_file.id, redirect=True))
    assert staged.redirect_url == "https://s3/meta"
    assert presign.call_args.args[0] is metadata_file
    assert presign.call_args.kwargs == metadata_file.object_store_path_kwargs()


def test_metadata_file_of_a_dataset_that_is_not_an_input_is_refused(app, manager):
    hda, not_an_input = _stored_hda(app), _stored_hda(app)
    metadata_file = _stored_metadata_file(app, not_an_input)
    job = _running_job(app, hda)
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.staged_input(**_signed(app, job, "metadata_file", metadata_file.id))

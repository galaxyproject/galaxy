import os
import time
from unittest import mock
from urllib.parse import (
    parse_qs,
    urlparse,
)

import pytest
from sqlalchemy import event

from galaxy import exceptions
from galaxy.managers.job_object_staging import (
    input_url,
    JobObjectStagingManager,
)
from galaxy.model import (
    Dataset,
    HistoryDatasetAssociation,
    Job,
    LibraryDatasetDatasetAssociation,
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


def _signed(app, job, kind, object_id, expires=LATER, redirect=False, path=""):
    """What a runner's request carries, read back from the URL the manager issues."""
    url = urlparse(input_url(app.security, GALAXY_URL, job.id, kind, object_id, expires, redirect=redirect, path=path))
    query = parse_qs(url.query)
    return dict(
        job_id=job.id,
        kind=kind,
        object_id=object_id,
        expires=int(query["exp"][0]),
        signature=query["sig"][0],
        redirect=query.get("redirect") == ["1"],
        path=query.get("path", [""])[0],
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


@pytest.mark.parametrize(
    "redirect,head", [(False, False), (True, False), (False, True)], ids=["get", "redirect", "head"]
)
def test_input_missing_from_the_object_store_is_not_found(app, manager, redirect, head):
    # Not an empty input: stores report a missing object's size as 0.
    hda = HistoryDatasetAssociation(sa_session=app.model.session, create_dataset=True)
    app.model.session.add(hda)
    job = _running_job(app, hda)
    with mock.patch.object(app.object_store, "get_direct_download_url", return_value="https://s3/signed"):
        with pytest.raises(exceptions.ObjectNotFound):
            manager.staged_input(**_signed(app, job, "dataset", _dataset(hda).id, redirect=redirect), head=head)


def _stage_in_a_fresh_session(app, manager, request) -> tuple[int, set[int]]:
    """Stage as a new web request would: the queries it takes, and the ids of the datasets it loads."""
    app.model.session.expunge_all()
    statements: list[str] = []
    loaded: set[int] = set()

    def record_statement(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    def record_load(dataset, context):
        loaded.add(dataset.id)

    engine = app.model.session.get_bind()
    event.listen(engine, "before_cursor_execute", record_statement)
    event.listen(Dataset, "load", record_load)
    try:
        manager.staged_input(**request, head=True)
    finally:
        event.remove(engine, "before_cursor_execute", record_statement)
        event.remove(Dataset, "load", record_load)
    return len(statements), loaded


# A job's inputs can number thousands, and each of their files is staged with its own request.


def test_staging_request_loads_only_the_input_it_is_for(app, manager):
    hdas = [_stored_hda(app) for _ in range(5)]
    input_id = _dataset(hdas[-1]).id
    request = _signed(app, _running_job(app, *hdas), "dataset", input_id)
    _, loaded = _stage_in_a_fresh_session(app, manager, request)
    assert loaded == {input_id}


def test_metadata_file_request_takes_as_many_queries_however_many_inputs_the_job_has(app, manager):
    def queries(input_count):
        hdas = [_stored_hda(app) for _ in range(input_count)]
        indexes = [_stored_metadata_file(app, hda) for hda in hdas]
        request = _signed(app, _running_job(app, *hdas), "metadata_file", indexes[-1].id)
        return _stage_in_a_fresh_session(app, manager, request)[0]

    assert queries(5) == queries(1)


def test_input_from_a_library_is_served(app, manager):
    ldda = LibraryDatasetDatasetAssociation(sa_session=app.model.session, create_dataset=True)
    app.model.session.add(ldda)
    app.model.session.commit()
    assert ldda.dataset is not None
    _store(app, ldda.dataset, CONTENT)
    job = Job()
    job.state = Job.states.RUNNING
    job.add_input_library_dataset("input", ldda)
    app.model.session.add(job)
    app.model.session.commit()
    staged = manager.staged_input(**_signed(app, job, "dataset", ldda.dataset.id))
    assert staged.path is not None
    with open(staged.path, "rb") as f:
        assert f.read() == CONTENT


def test_redirect_mode_answers_with_a_presigned_url(app, manager):
    hda = _stored_hda(app)
    job = _running_job(app, hda)
    with mock.patch.object(app.object_store, "get_direct_download_url", return_value="https://s3/signed") as presign:
        staged = manager.staged_input(**_signed(app, job, "dataset", _dataset(hda).id, redirect=True))
    assert staged.redirect_url == "https://s3/signed"
    assert presign.call_args.args[0] is _dataset(hda)


def test_redirect_mode_asks_for_a_presigned_url_that_lasts_minutes(app, manager):
    # Galaxy cannot revoke a presigned URL once the job ends, and the runner needs one only for the
    # request it follows the redirect with: it asks Galaxy again to resume or retry.
    hda = _stored_hda(app)
    job = _running_job(app, hda)
    with mock.patch.object(app.object_store, "get_direct_download_url", return_value="https://s3/signed") as presign:
        manager.staged_input(**_signed(app, job, "dataset", _dataset(hda).id, redirect=True))
    assert 0 < presign.call_args.kwargs["expires_in"] <= 15 * 60


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
    """A BAM index stored for ``hda``, which its metadata names."""
    hda.extension = "bam"
    metadata_file = MetadataFile(dataset=hda, name="bam_index")
    app.model.session.add(metadata_file)
    app.model.session.commit()
    source = os.path.join(app.config.new_file_path, "metadata_source")
    with open(source, "wb") as f:
        f.write(content)
    metadata_file.update_from_file(source)
    hda.metadata.bam_index = metadata_file
    app.model.session.commit()
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
    assert metadata_file.object_store_path_kwargs().items() <= presign.call_args.kwargs.items()


def test_metadata_file_of_a_dataset_that_is_not_an_input_is_refused(app, manager):
    hda, not_an_input = _stored_hda(app), _stored_hda(app)
    metadata_file = _stored_metadata_file(app, not_an_input)
    job = _running_job(app, hda)
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.staged_input(**_signed(app, job, "metadata_file", metadata_file.id))


def test_metadata_file_an_input_names_by_a_uuid_another_dataset_shares_is_served(app, manager):
    # Metadata file uuids are not unique in existing databases, e.g. after importing a history twice.
    # An input naming its index by uuid resolves to the oldest row, which may belong to another dataset.
    first_import, input_hda = _stored_hda(app), _stored_hda(app)
    first_index = _stored_metadata_file(app, first_import)
    _stored_metadata_file(app, input_hda).uuid = first_index.uuid
    input_hda.metadata.bam_index = str(first_index.uuid)
    app.model.session.commit()
    job = _running_job(app, input_hda)

    # The index the tool reads, and so the one the runner issues a URL for.
    assert input_hda.metadata.bam_index is first_index
    staged = manager.staged_input(**_signed(app, job, "metadata_file", first_index.id))
    with open(staged.path, "rb") as f:
        assert f.read() == b"bam index"


def _stored_extra_files(app, hda, files) -> dict[str, bytes]:
    dataset = _dataset(hda)
    for name, content in files.items():
        _store(app, dataset, content, extra_dir=dataset.extra_files_path_name, alt_name=name)
    return files


EXTRA_FILES = {"Sequences": b"sequences", "sub/deep.txt": b"deep"}


@pytest.mark.parametrize("name", EXTRA_FILES)
def test_input_extra_file_is_served_from_its_path_within_the_dataset(app, manager, name):
    hda = _stored_hda(app)
    _stored_extra_files(app, hda, EXTRA_FILES)
    job = _running_job(app, hda)
    staged = manager.staged_input(**_signed(app, job, "extra_file", _dataset(hda).id, path=name))
    with open(staged.path, "rb") as f:
        assert f.read() == EXTRA_FILES[name]
    assert staged.size == len(EXTRA_FILES[name])


def test_input_extra_file_is_presigned_at_its_path_within_the_dataset(app, manager):
    hda = _stored_hda(app)
    _stored_extra_files(app, hda, EXTRA_FILES)
    job = _running_job(app, hda)
    with mock.patch.object(app.object_store, "get_direct_download_url", return_value="https://s3/extra") as presign:
        staged = manager.staged_input(
            **_signed(app, job, "extra_file", _dataset(hda).id, redirect=True, path="sub/deep.txt")
        )
    assert staged.redirect_url == "https://s3/extra"
    assert presign.call_args.args[0] is _dataset(hda)
    path_kwargs = dict(extra_dir=_dataset(hda).extra_files_path_name, alt_name="sub/deep.txt")
    assert path_kwargs.items() <= presign.call_args.kwargs.items()


def test_extra_file_url_serves_only_the_file_it_was_issued_for(app, manager):
    hda = _stored_hda(app)
    _stored_extra_files(app, hda, EXTRA_FILES)
    job = _running_job(app, hda)
    request = {**_signed(app, job, "extra_file", _dataset(hda).id, path="Sequences"), "path": "sub/deep.txt"}
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.staged_input(**request)


def test_extra_file_of_a_dataset_that_is_not_an_input_is_refused(app, manager):
    hda, not_an_input = _stored_hda(app), _stored_hda(app)
    _stored_extra_files(app, not_an_input, EXTRA_FILES)
    job = _running_job(app, hda)
    with pytest.raises(exceptions.ItemAccessibilityException):
        manager.staged_input(**_signed(app, job, "extra_file", _dataset(not_an_input).id, path="Sequences"))

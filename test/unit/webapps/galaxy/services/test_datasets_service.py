from typing import cast
from unittest.mock import MagicMock

import pytest

from galaxy.exceptions import InternalServerError
from galaxy.webapps.galaxy.services.datasets import (
    DatasetsService,
    is_direct_download_candidate,
)


@pytest.mark.parametrize(
    ("filename", "to_ext", "raw", "offset", "ck_size", "is_archive", "expected"),
    [
        # plain download (floppy disk / bioblend) -> candidate
        (None, "data", False, None, None, False, True),
        # raw byte access of the main file -> candidate
        (None, None, True, None, None, False, True),
        # preview / display (no to_ext, not raw) -> not a candidate
        (None, None, False, None, None, False, False),
        # extra-files access -> not a candidate
        ("index.html", None, True, None, None, False, False),
        ("subfile", "data", False, None, None, False, False),
        # chunked display -> not a candidate
        (None, "data", False, 0, None, False, False),
        (None, "data", False, None, 1024, False, False),
        # composite/archived datatypes are zipped through Galaxy -> not a candidate
        (None, "data", False, None, None, True, False),
        (None, None, True, None, None, True, False),
    ],
)
def test_is_direct_download_candidate(filename, to_ext, raw, offset, ck_size, is_archive, expected):
    assert is_direct_download_candidate(filename, to_ext, raw, offset, ck_size, is_archive) is expected


def _service_for_display(
    *,
    data_stream=None,
    is_archive: bool = False,
    remote_size: int = 4,
):
    """Build a DatasetsService whose object store yields ``data_stream`` for the dataset."""
    service = DatasetsService(*(MagicMock() for _ in range(10)))
    dataset_instance = MagicMock()
    dataset_instance.datatype.is_archive_download.return_value = is_archive
    dataset_instance.datatype.download_content_disposition.return_value = 'attachment; filename="Galaxy1.txt"'
    dataset_instance.datatype.display_data.return_value = ("display-data", {})
    cast(MagicMock, service.hda_manager).get_accessible.return_value = dataset_instance

    trans = MagicMock()
    trans.app.object_store.get_data_stream.return_value = data_stream
    trans.app.object_store.size.return_value = remote_size
    return service, trans, dataset_instance


def test_display_streams_whole_file_download_from_object_store():
    chunks = iter([b"chun", b"ked"])
    service, trans, dataset_instance = _service_for_display(data_stream=chunks, remote_size=7)

    rval, headers = service.display(trans, 1, to_ext="txt", allow_stream=True)

    # The object-store stream is handed back untouched -- no pull into cache, no datatype processing.
    assert rval is chunks
    dataset_instance.datatype.display_data.assert_not_called()
    assert headers["content-type"] == "application/octet-stream"
    assert headers["Content-Disposition"] == 'attachment; filename="Galaxy1.txt"'
    # Content-Length comes from the store so the client can show download progress.
    assert headers["Content-Length"] == "7"
    # A forward-only stream cannot answer range requests, so it must not claim it can.
    assert "accept-ranges" not in headers


def test_display_closes_object_store_stream_when_logging_fails():
    class ClosableBody:
        def __init__(self):
            self.closed = False

        def __iter__(self):
            return iter([b"data"])

        def close(self):
            self.closed = True

    body = ClosableBody()
    service, trans, _ = _service_for_display(data_stream=body)
    trans.log_event.side_effect = RuntimeError("could not log download")

    with pytest.raises(InternalServerError):
        service.display(trans, 1, to_ext="txt", allow_stream=True)

    assert body.closed is True


def test_display_omits_content_length_when_object_store_size_is_unknown():
    chunks = iter([b"data"])
    service, trans, _ = _service_for_display(data_stream=chunks, remote_size=0)

    _, headers = service.display(trans, 1, to_ext="txt", allow_stream=True)

    assert "Content-Length" not in headers


def test_display_does_not_stream_when_caller_needs_random_access():
    service, trans, dataset_instance = _service_for_display(data_stream=iter([b"data"]))

    # allow_stream=False is how a HEAD or Range request (and every legacy caller) asks for a
    # seekable file rather than a one-shot stream.
    rval, _ = service.display(trans, 1, to_ext="txt", allow_stream=False)

    trans.app.object_store.get_data_stream.assert_not_called()
    dataset_instance.datatype.display_data.assert_called_once()
    assert rval == "display-data"


def test_display_falls_back_when_object_store_cannot_stream():
    service, trans, dataset_instance = _service_for_display(data_stream=None)

    rval, _ = service.display(trans, 1, to_ext="txt", allow_stream=True)

    trans.app.object_store.get_data_stream.assert_called_once()
    dataset_instance.datatype.display_data.assert_called_once()
    assert rval == "display-data"


def test_display_does_not_stream_previews():
    service, trans, dataset_instance = _service_for_display(data_stream=iter([b"data"]))

    # No to_ext: a preview is processed by the datatype, not served as stored bytes.
    service.display(trans, 1, allow_stream=True)

    trans.app.object_store.get_data_stream.assert_not_called()
    dataset_instance.datatype.display_data.assert_called_once()


def test_display_does_not_stream_archive_downloads():
    service, trans, dataset_instance = _service_for_display(data_stream=iter([b"data"]), is_archive=True)

    # Composite/archived datatypes are zipped on the fly, so the stored object is not what is served.
    service.display(trans, 1, to_ext="txt", allow_stream=True)

    trans.app.object_store.get_data_stream.assert_not_called()
    dataset_instance.datatype.display_data.assert_called_once()


def test_display_does_not_stream_raw_requests():
    service, trans, _ = _service_for_display(data_stream=iter([b"data"]))

    service.display(trans, 1, to_ext="txt", raw=True, allow_stream=True)

    trans.app.object_store.get_data_stream.assert_not_called()

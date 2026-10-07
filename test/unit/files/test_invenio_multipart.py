"""Unit tests for Invenio multipart upload functionality."""

from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from galaxy.files.sources.invenio import (
    _LimitedFileReader,
    calculate_multipart_params,
    InvenioRepositoryInteractor,
    InvenioRequestError,
    MAX_UPLOAD_PART_SIZE,
    MAX_UPLOAD_PARTS,
    MIN_UPLOAD_PART_SIZE,
)


class TestCalculateMultipartParams:
    """Tests for calculate_multipart_params function."""

    def test_calculate_multipart_params_zero_byte(self):
        """Zero-byte files return minimum part size."""
        parts, part_size = calculate_multipart_params(0)
        assert parts == 1
        assert part_size == MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_small_file(self):
        """Files under 5 MiB should use minimum part size."""
        # 2 MiB file
        file_size = 2 * 1024 * 1024
        parts, part_size = calculate_multipart_params(file_size)
        assert parts == 1
        assert part_size == MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_medium_file(self):
        """Files between 5 MiB and 10 MiB."""
        # 7.5 MiB file
        file_size = 7 * 1024 * 1024 + 512 * 1024
        parts, part_size = calculate_multipart_params(file_size)
        assert parts == 2
        assert part_size == MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_large_file(self):
        """Large files requiring multiple parts."""
        # 25 MiB file
        file_size = 25 * 1024 * 1024
        parts, part_size = calculate_multipart_params(file_size)
        assert parts == 5
        assert part_size == MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_respects_max_parts(self):
        """Very large files should not exceed MAX_UPLOAD_PARTS."""
        # File larger than MAX_UPLOAD_PARTS * MIN_UPLOAD_PART_SIZE
        file_size = MAX_UPLOAD_PARTS * MIN_UPLOAD_PART_SIZE + MIN_UPLOAD_PART_SIZE
        parts, part_size = calculate_multipart_params(file_size)
        assert parts <= MAX_UPLOAD_PARTS
        assert part_size >= MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_extremely_large_file(self):
        """Files larger than the maximum uploadable size raise ValueError instead of truncating."""
        # 100 TiB file - exceeds theoretical s3 maximum (~48.8 TiB)
        file_size = 100 * 1024**4
        with pytest.raises(ValueError, match="exceeds the maximum multipart upload size"):
            calculate_multipart_params(file_size)

    def test_calculate_multipart_params_raises_at_max_boundary(self):
        """One byte over the maximum uploadable size raises; exactly at the max does not."""
        max_upload_size = MAX_UPLOAD_PARTS * MAX_UPLOAD_PART_SIZE
        # Exactly at the boundary is allowed (parts == MAX_UPLOAD_PARTS at MAX part size).
        parts, part_size = calculate_multipart_params(max_upload_size)
        assert parts == MAX_UPLOAD_PARTS
        assert part_size == MAX_UPLOAD_PART_SIZE
        # One byte over raises.
        with pytest.raises(ValueError):
            calculate_multipart_params(max_upload_size + 1)

    def test_calculate_multipart_params_respects_preferred_part_size(self):
        """Should use preferred part size when provided and valid."""
        # 150 MiB file with 100 MiB preferred part size
        file_size = 150 * 1024 * 1024
        preferred_part_size = 100 * 1024 * 1024  # 100 MiB
        parts, part_size = calculate_multipart_params(file_size, preferred_part_size)
        assert parts == 2
        assert part_size == preferred_part_size

    def test_calculate_multipart_params_preferred_too_small(self):
        """Should use minimum part size if preferred is too small."""
        # 100 MiB file with 1 MiB preferred part size (too small)
        file_size = 100 * 1024 * 1024
        preferred_part_size = 1 * 1024 * 1024  # 1 MiB - too small
        parts, part_size = calculate_multipart_params(file_size, preferred_part_size)
        assert part_size == MIN_UPLOAD_PART_SIZE  # Should be bumped to minimum

    def test_calculate_multipart_params_preferred_exceeds_max(self):
        """Should cap at MAX_UPLOAD_PART_SIZE if preferred exceeds it."""
        # Small file with huge preferred part size
        file_size = 100 * 1024 * 1024
        preferred_part_size = MAX_UPLOAD_PART_SIZE * 2  # Exceeds max
        parts, part_size = calculate_multipart_params(file_size, preferred_part_size)
        assert parts == 1
        assert part_size == MAX_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_exact_multiple(self):
        """File size that's an exact multiple of part size."""
        # Exactly 3 * MIN_UPLOAD_PART_SIZE
        file_size = 3 * MIN_UPLOAD_PART_SIZE
        parts, part_size = calculate_multipart_params(file_size)
        assert parts == 3
        assert part_size == MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_one_byte_over(self):
        """File size one byte over an exact multiple."""
        # 3 * MIN_UPLOAD_PART_SIZE + 1 byte
        file_size = 3 * MIN_UPLOAD_PART_SIZE + 1
        parts, part_size = calculate_multipart_params(file_size)
        assert parts == 4  # Need 4 parts for 3 full + 1 byte
        assert part_size == MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_at_boundary(self):
        """Test file at MAX_UPLOAD_PARTS boundary."""
        # Exactly at the boundary where we need to increase part size
        file_size = (MAX_UPLOAD_PARTS + 1) * MIN_UPLOAD_PART_SIZE
        parts, part_size = calculate_multipart_params(file_size)
        assert parts <= MAX_UPLOAD_PARTS
        # Part size should have increased
        assert part_size > MIN_UPLOAD_PART_SIZE


def _mock_response(status_code=200, json_data=None, text=""):
    """Create a mock requests.Response object."""
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    if json_data is not None:
        response.json.return_value = json_data
    return response


def _make_interactor():
    """Create an InvenioRepositoryInteractor with a minimal mock plugin."""
    plugin = MagicMock()
    plugin.label = "test-invenio"
    plugin.get_uri_root.return_value = "inveniordm://test"
    return InvenioRepositoryInteractor("https://invenio.example.org", plugin)


def _make_context(config=None):
    """Create a mock runtime context with the given config."""
    context = MagicMock()
    context.config = config or MagicMock(
        multipart_threshold=None,
        multipart_chunk_size=None,
        default_resource_type=None,
        token="test-token",
        public_name="Doe, Jane",
    )
    return context


def _make_draft_record():
    """Standard draft record response with files link."""
    return {"links": {"files": "https://invenio.example.org/api/records/abc/files"}}


def _make_single_upload_entry():
    """File entry returned after POST for single upload."""
    return {
        "key": "test.txt",
        "links": {
            "content": "https://invenio.example.org/api/records/abc/files/content",
            "commit": "https://invenio.example.org/api/records/abc/files/commit",
        },
    }


def _make_multipart_entries(num_parts):
    """File entry returned after POST for multipart upload, with part links."""
    parts = [{"part": i, "url": f"https://invenio.example.org/parts/{i}"} for i in range(num_parts)]
    return {
        "key": "test.txt",
        "links": {
            "commit": "https://invenio.example.org/api/records/abc/files/commit",
            "self": "https://invenio.example.org/api/records/abc/files/test.txt",
            "parts": parts,
        },
    }


class TestUploadFileSingle:
    """Tests for _upload_file_single."""

    def test_upload_file_single_success(self, tmp_path):
        """Verify POST (metadata), PUT (content), POST (commit) sequence."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"hello world")

        interactor = _make_interactor()
        context = _make_context()

        with (
            patch.object(interactor, "_get_draft_record", return_value=_make_draft_record()),
            patch.object(interactor, "_get_request_headers", return_value={"Authorization": "Bearer x"}),
            patch("galaxy.files.sources.invenio.requests") as mock_requests,
        ):
            mock_requests.post.side_effect = [
                _mock_response(201, {"entries": [_make_single_upload_entry()]}),  # metadata
                _mock_response(200),  # commit
            ]
            mock_requests.put.return_value = _mock_response(200)

            interactor._upload_file_single("abc", "test.txt", str(file_path), context)

            assert mock_requests.post.call_count == 2
            assert mock_requests.put.call_count == 1

    def test_upload_file_single_propagates_413_as_typed_error(self, tmp_path):
        """A 413 from the content PUT surfaces as an InvenioRequestError carrying the status code."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"hello world")

        interactor = _make_interactor()
        context = _make_context()

        with (
            patch.object(interactor, "_get_draft_record", return_value=_make_draft_record()),
            patch.object(interactor, "_get_request_headers", return_value={"Authorization": "Bearer x"}),
            patch("galaxy.files.sources.invenio.requests") as mock_requests,
        ):
            mock_requests.post.return_value = _mock_response(201, {"entries": [_make_single_upload_entry()]})
            mock_requests.put.return_value = _mock_response(413)

            with pytest.raises(InvenioRequestError) as exc_info:
                interactor._upload_file_single("abc", "test.txt", str(file_path), context)

            assert exc_info.value.status_code == 413


class TestUploadFileMultipart:
    """Tests for _upload_file_multipart."""

    def test_upload_file_multipart_success(self, tmp_path):
        """Verify transfer metadata, part uploads, and commit call."""
        file_size = 3 * MIN_UPLOAD_PART_SIZE
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"x" * file_size)

        interactor = _make_interactor()
        context = _make_context(
            config=MagicMock(
                multipart_threshold=1,
                multipart_chunk_size=None,
                default_resource_type=None,
                token="test-token",
                public_name="Doe, Jane",
            )
        )

        entries = _make_multipart_entries(3)

        with (
            patch.object(interactor, "_get_draft_record", return_value=_make_draft_record()),
            patch.object(interactor, "_get_request_headers", return_value={"Authorization": "Bearer x"}),
            patch.object(interactor, "_upload_single_part") as mock_upload_part,
            patch("galaxy.files.sources.invenio.requests") as mock_requests,
        ):
            mock_requests.post.side_effect = [
                _mock_response(201, {"entries": [entries]}),  # initial POST
                _mock_response(200),  # commit POST
            ]

            interactor._upload_file_multipart("abc", "test.txt", str(file_path), file_size, context)

            # Verify transfer metadata in the initial POST
            initial_post_args = mock_requests.post.call_args_list[0]
            sent_metadata = initial_post_args.kwargs["json"][0]
            assert sent_metadata["key"] == "test.txt"
            assert sent_metadata["size"] == file_size
            assert sent_metadata["transfer"]["type"] == "M"
            assert sent_metadata["transfer"]["parts"] == 3
            assert sent_metadata["transfer"]["part_size"] == MIN_UPLOAD_PART_SIZE

            # All 3 parts uploaded
            assert mock_upload_part.call_count == 3
            # Commit called (second POST)
            assert mock_requests.post.call_count == 2

    def test_upload_file_multipart_wrong_part_count_from_server(self, tmp_path):
        """Server returning fewer part links than expected should raise."""
        file_size = 3 * MIN_UPLOAD_PART_SIZE
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"x" * file_size)

        interactor = _make_interactor()
        context = _make_context(
            config=MagicMock(
                multipart_threshold=1,
                multipart_chunk_size=None,
                default_resource_type=None,
                token="test-token",
                public_name="Doe, Jane",
            )
        )

        # Server returns only 2 part links instead of 3
        entries = _make_multipart_entries(2)

        with (
            patch.object(interactor, "_get_draft_record", return_value=_make_draft_record()),
            patch.object(interactor, "_get_request_headers", return_value={"Authorization": "Bearer x"}),
            patch("galaxy.files.sources.invenio.requests") as mock_requests,
        ):
            mock_requests.post.return_value = _mock_response(201, {"entries": [entries]})

            with pytest.raises(Exception, match="2 part URLs"):
                interactor._upload_file_multipart("abc", "test.txt", str(file_path), file_size, context)


class TestUploadSinglePart:
    """Tests for _upload_single_part byte-range streaming."""

    def test_upload_single_part_streams_correct_byte_range(self, tmp_path):
        """Verify the uploaded data matches the expected byte slice."""
        data = b"0123456789ABCDEF" * 4  # 64 bytes
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(data)

        interactor = _make_interactor()
        part_size = 16
        part_info = {"part": 2, "url": "https://invenio.example.org/parts/2"}

        captured_data = bytearray()

        def fake_put(url, data=None, **kwargs):
            captured_data.extend(data.read())
            return _mock_response(200)

        with patch("galaxy.files.sources.invenio.requests") as mock_requests:
            mock_requests.put.side_effect = fake_put

            interactor._upload_single_part(str(file_path), len(data), part_size, 2, part_info, {})

            # Part 2 = bytes 32-48
            assert bytes(captured_data) == data[32:48]


class TestLimitedFileReader:
    """Tests for _LimitedFileReader streaming wrapper."""

    def test_read_limited_bytes(self, tmp_path):
        """Reader should only return the specified number of bytes."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"0123456789")

        with open(file_path, "rb") as f:
            f.seek(3)
            reader = _LimitedFileReader(f, 4)
            assert reader.read() == b"3456"

    def test_read_in_chunks(self, tmp_path):
        """Reader should serve data in small chunks without over-reading."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"0123456789")

        with open(file_path, "rb") as f:
            f.seek(2)
            reader = _LimitedFileReader(f, 5)
            assert reader.read(2) == b"23"
            assert reader.read(2) == b"45"
            assert reader.read(2) == b"6"  # only 1 byte remaining
            assert reader.read(2) == b""  # now exhausted

    def test_len_reports_remaining(self, tmp_path):
        """__len__ should report remaining bytes."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"0123456789")

        with open(file_path, "rb") as f:
            f.seek(1)
            reader = _LimitedFileReader(f, 5)
            assert len(reader) == 5
            reader.read(2)
            assert len(reader) == 3


class TestUploadFileToDraftContainerRouting:
    """Tests for upload_file_to_draft_container threshold routing."""

    def test_routes_to_single_when_below_threshold(self, tmp_path):
        """Files below threshold should use single upload."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"small")

        interactor = _make_interactor()
        context = _make_context(
            config=MagicMock(
                multipart_threshold=100,
                multipart_chunk_size=None,
                default_resource_type=None,
                token="test-token",
                public_name="Doe, Jane",
            )
        )

        with patch.object(interactor, "_upload_file_single") as mock_single:
            interactor.upload_file_to_draft_container("abc", "test.txt", str(file_path), context)
            mock_single.assert_called_once()

    def test_routes_to_multipart_when_above_threshold(self, tmp_path):
        """Files at or above threshold should use multipart upload."""
        file_size = 2 * 1024 * 1024  # 2 MiB
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"x" * file_size)

        interactor = _make_interactor()
        context = _make_context(
            config=MagicMock(
                multipart_threshold=1,  # 1 MB threshold, file is 2 MB
                multipart_chunk_size=None,
                default_resource_type=None,
                token="test-token",
                public_name="Doe, Jane",
            )
        )

        with patch.object(interactor, "_upload_file_multipart") as mock_multipart:
            interactor.upload_file_to_draft_container("abc", "test.txt", str(file_path), context)
            mock_multipart.assert_called_once()
            # Verify file_size is passed through
            assert mock_multipart.call_args[0][3] == file_size

    def test_routes_to_single_when_no_threshold(self, tmp_path):
        """No threshold configured should always use single upload."""
        file_size = 100 * 1024 * 1024  # 100 MiB
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"x" * file_size)

        interactor = _make_interactor()
        context = _make_context()

        with patch.object(interactor, "_upload_file_single") as mock_single:
            interactor.upload_file_to_draft_container("abc", "test.txt", str(file_path), context)
            mock_single.assert_called_once()

    def test_upload_file_single_413_router_raises_helpful_error(self, tmp_path):
        """Router should wrap 413 with actionable multipart_threshold message."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"hello world")

        interactor = _make_interactor()
        context = _make_context(
            config=MagicMock(
                multipart_threshold=None,  # No threshold configured
                multipart_chunk_size=None,
                default_resource_type=None,
                token="test-token",
                public_name="Doe, Jane",
            )
        )

        with (
            patch.object(interactor, "_get_draft_record", return_value=_make_draft_record()),
            patch.object(interactor, "_get_request_headers", return_value={"Authorization": "Bearer x"}),
            patch("galaxy.files.sources.invenio.requests") as mock_requests,
        ):
            mock_requests.post.return_value = _mock_response(201, {"entries": [_make_single_upload_entry()]})
            mock_requests.put.return_value = _mock_response(413)

            with pytest.raises(Exception, match="multipart_threshold"):
                interactor.upload_file_to_draft_container("abc", "test.txt", str(file_path), context)

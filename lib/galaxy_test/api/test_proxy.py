import pytest
import requests

from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase

REMOTE_URL_TO_TEST = (
    "https://github.com/galaxyproject/galaxy/raw/6e7427e8e2e070d4ab491a6cce5a59b6b6a62a08/test-data/4.bed.zip"
)
EXPECTED_HEADERS = {
    "content-length": "198",
    "content-type": "application/zip",
    "accept-ranges": "bytes",
}
ZIP_MAGIC_NUMBER = b"PK\x03\x04"
TRAINING_URL = "https://training.galaxyproject.org/training-material/topics/introduction/tutorials/galaxy-intro-short/tutorial.html"


class TestProxyApi(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def _get_zip_url(self, mock_http_server):
        return mock_http_server.get_url(
            remote_url=REMOTE_URL_TO_TEST,
            file_path="test-data/4.bed.zip",
            content_type="application/zip",
            support_head=True,
            support_ranges=True,
        )

    def test_proxy_head_request(self, mock_http_server):
        url = self._get_zip_url(mock_http_server)
        response = self._head(f"proxy?url={url}")
        self._assert_status_code_is_ok(response)
        assert response.headers["content-length"] == EXPECTED_HEADERS["content-length"]
        assert response.headers["content-type"] == EXPECTED_HEADERS["content-type"]
        assert response.headers["accept-ranges"] == EXPECTED_HEADERS["accept-ranges"]

    def test_proxy_get_request(self, mock_http_server):
        url = self._get_zip_url(mock_http_server)
        response = self._get(f"proxy?url={url}")
        self._assert_status_code_is_ok(response)
        assert response.headers["content-length"] == EXPECTED_HEADERS["content-length"]
        assert response.headers["content-type"] == EXPECTED_HEADERS["content-type"]
        assert response.headers["accept-ranges"] == EXPECTED_HEADERS["accept-ranges"]
        assert len(response.content) == int(EXPECTED_HEADERS["content-length"])

    def test_proxy_get_request_with_range(self, mock_http_server):
        url = self._get_zip_url(mock_http_server)
        request_range = "bytes=0-3"
        response = self._get(f"proxy?url={url}", headers={"range": request_range})
        self._assert_status_code_is(response, 206)
        assert response.headers["accept-ranges"] == "bytes"
        assert response.headers["content-length"] == "4"
        assert response.headers["content-range"].startswith("bytes 0-3/")
        assert response.content == ZIP_MAGIC_NUMBER

    def test_anonymous_user_cannot_access_proxy(self):
        response = self._get(f"proxy?url={REMOTE_URL_TO_TEST}", anon=True)
        self._assert_status_code_is(response, 403)
        assert response.json()["err_msg"] == "Anonymous users are not allowed to access this endpoint"

    @pytest.mark.parametrize(
        "invalid_url",
        [
            "htp://invalid-url",
            "http:/missing-slash.com",
            "//missing-scheme.com",
            "invalid-url",
            "https://first.url\nhttps://second.url",
            "https://first.url https://second.url",
            "https://first.urlhttps://second.url",
            # Schemes other than http and https are not allowed
            "ftp://not-allowed.com",
            "file://etc/passwd",
        ],
    )
    def test_invalid_url_format(self, invalid_url: str):
        response = self._get(f"proxy?url={invalid_url}")
        self._assert_status_code_is(response, 400)
        assert response.json()["err_msg"] == "Invalid URL format."

    @pytest.mark.parametrize(
        "url_with_nonprintable",
        [
            f"\t{REMOTE_URL_TO_TEST}",  # Tab at beginning
            f"{REMOTE_URL_TO_TEST}\t",  # Tab at end
            "https://example.com/path\twith\ttab",  # Tabs in path
            "https://exam\tple.com/path",  # Tab in domain
            f"\r\n{REMOTE_URL_TO_TEST}",  # CRLF at beginning
            f"{REMOTE_URL_TO_TEST}\r\n",  # CRLF at end
        ],
    )
    def test_url_with_nonprintable_characters(self, url_with_nonprintable: str):
        """Test that URLs with non-printable characters return 400 instead of 500.

        When non-printable characters like tabs or newlines are present in the URL,
        they should be caught by validation and return 400, not trigger a 500 error.

        This test manually constructs the URL with unencoded non-printable characters
        to reproduce the actual issue that occurs when clients send malformed URLs,
        bypassing the test framework's automatic URL encoding.
        """
        base_url = self.galaxy_interactor.api_url
        full_url = f"{base_url}/proxy?url={url_with_nonprintable}"
        headers = self.galaxy_interactor.api_key_header(key=None, admin=False, anon=False, headers=None)
        # Filter out None values for requests compatibility
        filtered_headers = {k: v for k, v in headers.items() if v is not None}
        response = requests.get(full_url, headers=filtered_headers)

        self._assert_status_code_is(response, 400)
        assert response.json()["err_msg"] == "Invalid URL format."

    def test_proxy_handles_encoding(self):
        """Test handling of responses with content-encoding and proper header filtering.

        The TRAINING_URL URL triggered the 'Too much data for declared Content-Length' error because
        the response included a content-encoding header (gzip) even though the content was
        already decompressed by the requests library.
        """
        response = self._get(f"proxy?url={TRAINING_URL}")
        self._assert_status_code_is_ok(response)
        # Verify we got HTML content
        assert b"<!DOCTYPE" in response.content or b"<html" in response.content.lower()
        # Verify the response has actual content
        assert len(response.content) > 0
        # Verify content-encoding header was properly filtered out (no double decompression)
        assert "content-encoding" not in response.headers

    def test_proxy_validates_redirects(self, mock_http_server):
        """Test that redirects to invalid schemes are blocked."""
        url = mock_http_server.get_url(
            remote_url="https://evil.com/redirect",
            status=302,
            response_headers={"Location": "file://internal-server/secret-files"},
        )
        response = self._get(f"proxy?url={url}")
        self._assert_status_code_is(response, 400)
        assert "Invalid URL format" in response.json()["err_msg"]

    def test_proxy_follows_valid_redirects(self, mock_http_server):
        """Test that valid redirects are followed after validation."""
        final_url = mock_http_server.get_url(
            remote_url="https://example.com/final",
            status=200,
            body="test content",
            content_type="text/plain",
        )
        redirect_url = mock_http_server.get_url(
            remote_url="https://example.com/redirect",
            status=301,
            response_headers={"Location": final_url},
        )
        response = self._get(f"proxy?url={redirect_url}")
        self._assert_status_code_is_ok(response)
        assert b"test content" in response.content

    def test_proxy_blocks_too_many_redirects(self, mock_http_server):
        """Test that excessive redirects are blocked to prevent redirect loops."""
        url = mock_http_server.get_url(
            remote_url="https://example.com/loop",
            status=302,
            redirect_to_self=True,
        )
        response = self._get(f"proxy?url={url}")
        self._assert_status_code_is(response, 400)
        assert "Too many redirects" in response.json()["err_msg"]

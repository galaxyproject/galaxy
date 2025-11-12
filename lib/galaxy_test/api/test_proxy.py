from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest
import requests

from galaxy.util.unittest_utils import skip_if_github_down
from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase

URL_TO_TEST = "https://github.com/galaxyproject/galaxy/raw/6e7427e8e2e070d4ab491a6cce5a59b6b6a62a08/test-data/4.bed.zip"
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

    @skip_if_github_down
    def test_proxy_head_request(self):
        response = self._head(f"proxy?url={URL_TO_TEST}")
        self._assert_status_code_is_ok(response)
        assert response.headers["content-length"] == EXPECTED_HEADERS["content-length"]
        assert response.headers["content-type"] == EXPECTED_HEADERS["content-type"]
        assert response.headers["accept-ranges"] == EXPECTED_HEADERS["accept-ranges"]

    @skip_if_github_down
    def test_proxy_get_request(self):
        response = self._get(f"proxy?url={URL_TO_TEST}")
        self._assert_status_code_is_ok(response)
        assert response.headers["content-length"] == EXPECTED_HEADERS["content-length"]
        assert response.headers["content-type"] == EXPECTED_HEADERS["content-type"]
        assert response.headers["accept-ranges"] == EXPECTED_HEADERS["accept-ranges"]
        assert len(response.content) == int(EXPECTED_HEADERS["content-length"])

    @skip_if_github_down
    def test_proxy_get_request_with_range(self):
        request_range = "bytes=0-3"
        response = self._get(f"proxy?url={URL_TO_TEST}", headers={"range": request_range})
        self._assert_status_code_is(response, 206)
        assert response.headers["accept-ranges"] == "bytes"
        assert response.headers["content-length"] == "4"
        assert response.headers["content-range"].startswith("bytes 0-3/")
        assert response.content == ZIP_MAGIC_NUMBER

    def test_anonymous_user_cannot_access_proxy(self):
        response = self._get(f"proxy?url={URL_TO_TEST}", anon=True)
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
            f"\t{URL_TO_TEST}",  # Tab at beginning
            f"{URL_TO_TEST}\t",  # Tab at end
            "https://example.com/path\twith\ttab",  # Tabs in path
            "https://exam\tple.com/path",  # Tab in domain
            f"\r\n{URL_TO_TEST}",  # CRLF at beginning
            f"{URL_TO_TEST}\r\n",  # CRLF at end
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
        response = requests.get(full_url, headers=headers)

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

    @patch("galaxy.webapps.galaxy.api.proxy.httpx.AsyncClient")
    def test_proxy_validates_redirects(self, mock_client_class):
        """Test that redirects are validated."""
        # Create mock responses - redirect to a local file (invalid scheme)
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"location": "file://internal-server/secret-files"}
        redirect_response.aclose = AsyncMock()

        # Setup mock client
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value=redirect_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        # Attempt to proxy a URL that redirects to file:// (should be blocked)
        response = self._get("proxy?url=https://evil.com/redirect")

        # Should fail with 400 Bad Request due to invalid redirect URL scheme
        self._assert_status_code_is(response, 400)
        assert "Invalid URL format" in response.json()["err_msg"]

    @patch("galaxy.webapps.galaxy.api.proxy.httpx.AsyncClient")
    def test_proxy_follows_valid_redirects(self, mock_client_class):
        """Test that valid redirects are followed after validation."""
        # Create mock responses
        redirect_response = MagicMock()
        redirect_response.status_code = 301
        redirect_response.headers = {"location": "https://example.com/final"}
        redirect_response.aclose = AsyncMock()

        final_response = MagicMock()
        final_response.status_code = 200
        final_response.headers = {"content-type": "text/plain"}
        final_response.aclose = AsyncMock()

        # Create async generator for streaming
        async def mock_stream():
            yield b"test content"

        final_response.aiter_bytes = mock_stream

        # Setup mock client to return redirect first, then final response
        mock_client = MagicMock()
        mock_client.request = AsyncMock(side_effect=[redirect_response, final_response])
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        # Proxy a URL that redirects to a valid external URL
        response = self._get("proxy?url=https://example.com/redirect")

        # Should succeed and follow the redirect
        self._assert_status_code_is_ok(response)
        assert b"test content" in response.content

    @patch("galaxy.webapps.galaxy.api.proxy.httpx.AsyncClient")
    def test_proxy_blocks_too_many_redirects(self, mock_client_class):
        """Test that excessive redirects are blocked to prevent redirect loops."""
        # Create a mock response that always redirects
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"location": "https://example.com/loop"}
        redirect_response.aclose = AsyncMock()

        # Setup mock client
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value=redirect_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        # Attempt to proxy a URL that loops redirects
        response = self._get("proxy?url=https://example.com/loop")

        # Should fail with 400 Bad Request due to too many redirects
        self._assert_status_code_is(response, 400)
        assert "Too many redirects" in response.json()["err_msg"]

import pytest

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

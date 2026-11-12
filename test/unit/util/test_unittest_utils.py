from unittest import SkipTest

import pytest
import requests

from galaxy.util.unittest_utils import skip_on_network_error


def _raise_for_status(status_code: int) -> None:
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://api.anaconda.org/package/bioconda/samtools/files"
    response.raise_for_status()


@pytest.mark.parametrize("status_code", [429, 503, 523])
def test_skip_on_network_error_skips_unavailable_site(status_code):
    @skip_on_network_error
    def test():
        _raise_for_status(status_code)

    with pytest.raises(SkipTest, match=str(status_code)):
        test()


def test_skip_on_network_error_fails_on_client_error():
    @skip_on_network_error
    def test():
        _raise_for_status(404)

    with pytest.raises(requests.exceptions.HTTPError, match="404"):
        test()

from uuid import uuid4

from galaxy_test.base.api_asserts import assert_status_code_is
from ._framework import ApiTestCase


class TestShortTermStorageApi(ApiTestCase):
    def test_invalid_request_id_returns_400(self):
        invalid_uuid = "invalid_uuid"
        response = self._get(f"short_term_storage/{invalid_uuid}")
        assert_status_code_is(response, 400)

    def test_non_existent_request_id_returns_404(self):
        valid_uuid = uuid4()
        response = self._get(f"short_term_storage/{valid_uuid}")
        assert_status_code_is(response, 404)

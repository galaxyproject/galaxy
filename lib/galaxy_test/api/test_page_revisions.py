from galaxy.exceptions import error_codes
from .test_pages import BasePagesApiTestCase


class TestPageRevisionsApi(BasePagesApiTestCase):
    def test_create(self):
        page_json = self._create_valid_page_with_slug("pr1")
        revision_data = dict(content="<p>NewContent!</p>")
        page_revision_response = self._post(f"pages/{page_json['id']}/revisions", data=revision_data)
        self._assert_status_code_is(page_revision_response, 200)
        page_revision_json = page_revision_response.json()
        self._assert_has_keys(page_revision_json, "id", "content")

    def test_403_if_create_revision_on_unowned_page(self):
        page_json = self._create_valid_page_as("pr2@bx.psu.edu", "pr2")
        revision_data = dict(content="<p>NewContent!</p>")
        page_revision_response = self._post(f"pages/{page_json['id']}/revisions", data=revision_data)
        self._assert_status_code_is(page_revision_response, 403)

    def test_revision_index(self):
        page_json = self._create_valid_page_with_slug("pr3")
        revision_data = dict(content="<p>NewContent!</p>")
        revisions_url = f"pages/{page_json['id']}/revisions"
        self._post(revisions_url, data=revision_data)
        revisions_response = self._get(revisions_url)
        self._assert_status_code_is(revisions_response, 200)
        revisions_json = revisions_response.json()
        assert len(revisions_json) == 2  # Original revision and new one

    def test_malformed_id_if_index_unknown_page(self):
        revisions_url = f"pages/{self._random_key()}/revisions"
        revisions_response = self._get(revisions_url)
        self._assert_status_code_is(revisions_response, 400)
        self._assert_error_code_is(revisions_response, error_codes.error_codes_by_name["MALFORMED_ID"])

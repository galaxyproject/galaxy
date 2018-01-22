from galaxy.exceptions import error_codes
from .test_pages import BasePageApiTestCase


class PageRevisionsApiTestCase(BasePageApiTestCase):

    def test_create(self):
        page_json = self._create_valid_page_with_slug("pr1")
        revision_data = dict(content="<p>NewContent!</p>")
        page_revision_response = self._post("pages/%s/revisions" % page_json['id'], data=revision_data)
        self._assert_status_code_is(page_revision_response, 200)
        page_revision_json = page_revision_response.json()
        self._assert_has_keys(page_revision_json, 'id', 'content')

    def test_403_if_create_revision_on_unowned_page(self):
        page_json = self._create_valid_page_as("pr2@bx.psu.edu", "pr2")
        revision_data = dict(content="<p>NewContent!</p>")
        page_revision_response = self._post("pages/%s/revisions" % page_json['id'], data=revision_data)
        self._assert_status_code_is(page_revision_response, 403)

    def test_revision_index(self):
        page_json = self._create_valid_page_with_slug("pr3")
        revision_data = dict(content="<p>NewContent!</p>")
        revisions_url = "pages/%s/revisions" % page_json['id']
        self._post(revisions_url, data=revision_data)
        revisions_response = self._get(revisions_url)
        self._assert_status_code_is(revisions_response, 200)
        revisions_json = revisions_response.json()
        assert len(revisions_json) == 2  # Original revision and new one

    def test_404_if_index_unknown_page(self):
        revisions_url = "pages/%s/revisions" % self._random_key()
        revisions_response = self._get(revisions_url)
        self._assert_status_code_is(revisions_response, 404)
        self._assert_error_code_is(revisions_response, error_codes.USER_OBJECT_NOT_FOUND)

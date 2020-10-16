from requests import delete

from base import api  # noqa: I100,I202
from galaxy.exceptions import error_codes  # noqa: I201


class BasePageApiTestCase(api.ApiTestCase):

    def _create_valid_page_with_slug(self, slug):
        page_request = self._test_page_payload(slug=slug)
        page_response = self._post("pages", page_request)
        self._assert_status_code_is(page_response, 200)
        return page_response.json()

    def _create_valid_page_as(self, other_email, slug):
        run_as_user = self._setup_user(other_email)
        page_request = self._test_page_payload(slug=slug)
        page_request["run_as"] = run_as_user["id"]
        page_response = self._post("pages", page_request, admin=True)
        self._assert_status_code_is(page_response, 200)
        return page_response.json()

    def _test_page_payload(self, **kwds):
        request = dict(
            slug="mypage",
            title="MY PAGE",
            content="<p>Page!</p>",
        )
        request.update(**kwds)
        return request


class PageApiTestCase(BasePageApiTestCase):

    def test_create(self):
        response_json = self._create_valid_page_with_slug("mypage")
        self._assert_has_keys(response_json, "slug", "title", "id")

    def test_index(self):
        create_response_json = self._create_valid_page_with_slug("indexpage")
        assert self._users_index_has_page_with_id(create_response_json["id"])

    def test_index_doesnt_show_unavailable_pages(self):
        create_response_json = self._create_valid_page_as("others_page_index@bx.psu.edu", "otherspageindex")
        assert not self._users_index_has_page_with_id(create_response_json["id"])

    def test_cannot_create_pages_with_same_slug(self):
        page_request = self._test_page_payload(slug="mypage1")
        page_response_1 = self._post("pages", page_request)
        self._assert_status_code_is(page_response_1, 200)
        page_response_2 = self._post("pages", page_request)
        self._assert_status_code_is(page_response_2, 400)
        self._assert_error_code_is(page_response_2, error_codes.USER_SLUG_DUPLICATE)

    def test_page_requires_name(self):
        page_request = self._test_page_payload()
        del page_request['title']
        page_response = self._post("pages", page_request)
        self._assert_status_code_is(page_response, 400)
        self._assert_error_code_is(page_response, error_codes.USER_OBJECT_ATTRIBUTE_MISSING)

    def test_page_requires_slug(self):
        page_request = self._test_page_payload()
        del page_request['slug']
        page_response = self._post("pages", page_request)
        self._assert_status_code_is(page_response, 400)

    def test_delete(self):
        response_json = self._create_valid_page_with_slug("testdelete")
        delete_response = delete(self._api_url("pages/%s" % response_json['id'], use_key=True))
        self._assert_status_code_is(delete_response, 200)

    def test_404_on_delete_unknown_page(self):
        delete_response = delete(self._api_url("pages/%s" % self._random_key(), use_key=True))
        self._assert_status_code_is(delete_response, 404)
        self._assert_error_code_is(delete_response, error_codes.USER_OBJECT_NOT_FOUND)

    def test_403_on_delete_unowned_page(self):
        page_response = self._create_valid_page_as("others_page@bx.psu.edu", "otherspage")
        delete_response = delete(self._api_url("pages/%s" % page_response["id"], use_key=True))
        self._assert_status_code_is(delete_response, 403)
        self._assert_error_code_is(delete_response, error_codes.USER_DOES_NOT_OWN_ITEM)

    def test_show(self):
        response_json = self._create_valid_page_with_slug("pagetoshow")
        show_response = self._get("pages/%s" % response_json['id'])
        self._assert_status_code_is(show_response, 200)
        show_json = show_response.json()
        self._assert_has_keys(show_json, "slug", "title", "id")
        self.assertEqual(show_json["slug"], "pagetoshow")
        self.assertEqual(show_json["title"], "MY PAGE")
        self.assertEqual(show_json["content"], "<p>Page!</p>")

    def test_403_on_unowner_show(self):
        response_json = self._create_valid_page_as("others_page_show@bx.psu.edu", "otherspageshow")
        show_response = self._get("pages/%s" % response_json['id'])
        self._assert_status_code_is(show_response, 403)
        self._assert_error_code_is(show_response, error_codes.USER_DOES_NOT_OWN_ITEM)

    def _users_index_has_page_with_id(self, id):
        index_response = self._get("pages")
        self._assert_status_code_is(index_response, 200)
        pages = index_response.json()
        return id in (_["id"] for _ in pages)

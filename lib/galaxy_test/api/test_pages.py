from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)
from unittest import SkipTest
from uuid import uuid4

from requests import delete
from requests.models import Response

from galaxy.exceptions import error_codes
from galaxy_test.api._framework import ApiTestCase
from galaxy_test.api.sharable import SharingApiTests
from galaxy_test.base import api_asserts
from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_tool,
    WorkflowPopulator,
)


class BasePagesApiTestCase(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def _create_valid_page_with_slug(self, slug, **kwd) -> Dict[str, Any]:
        return self.dataset_populator.new_page(slug=slug, **kwd)

    def _create_valid_page_as(self, other_email, slug):
        run_as_user = self._setup_user(other_email)
        page_request = self._test_page_payload(slug=slug)
        page_response = self._post("pages", page_request, headers={"run-as": run_as_user["id"]}, admin=True, json=True)
        self._assert_status_code_is(page_response, 200)
        return page_response.json()

    def _test_page_payload(self, **kwds):
        return self.dataset_populator.new_page_payload(**kwds)


class TestPagesApi(BasePagesApiTestCase, SharingApiTests):
    api_name = "pages"

    def create(self, name: str) -> str:
        response_json = self._create_valid_page_with_slug(name)
        return response_json["id"]

    def test_create(self):
        response_json = self._create_valid_page_with_slug("mypage")
        self._assert_has_keys(response_json, "slug", "title", "id")

    @skip_without_tool("cat")
    def test_create_from_report(self):
        test_data = """
input_1:
  value: 1.bed
  type: File
"""
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input_1: data
outputs:
  output_1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input_1
""",
                test_data=test_data,
                history_id=history_id,
            )

            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            report_json = self.workflow_populator.workflow_report_json(workflow_id, invocation_id)
            assert "markdown" in report_json
            self._assert_has_keys(report_json, "markdown", "render_format")
            assert report_json["render_format"] == "markdown"
            markdown_content = report_json["markdown"]
            page_request = dict(
                slug="invocation-report",
                title="Invocation Report",
                invocation_id=invocation_id,
            )
            page_response = self._post("pages", page_request, json=True)
            self._assert_status_code_is(page_response, 200)
            page_response = page_response.json()
            show_response = self._get(f"pages/{page_response['id']}")
            self._assert_status_code_is(show_response, 200)
            show_json = show_response.json()
            self._assert_has_keys(show_json, "slug", "title", "id")
            assert show_json["slug"] == "invocation-report"
            assert show_json["title"] == "Invocation Report"
            assert show_json["content_format"] == "markdown"
            markdown_content = show_json["content"]
            assert "## Workflow Outputs" in markdown_content
            assert "## Workflow Inputs" in markdown_content
            assert "## About This Report" not in markdown_content

    def test_index(self):
        create_response_json = self._create_valid_page_with_slug("indexpage")
        assert self._users_index_has_page_with_id(create_response_json)

    def test_400_on_index_deleted_shared(self):
        response = self._index_raw(params=dict(show_shared=True, deleted=True))
        assert response.status_code == 400

    def test_index_deleted(self):
        response1 = self._create_valid_page_with_slug("indexdeletedpageundeleted")
        response2 = self._create_valid_page_with_slug("indexdeletedpagedeleted")
        assert self._users_index_has_page_with_id(response1)
        assert self._users_index_has_page_with_id(response2)
        delete_response = self._delete(f"pages/{response2['id']}")
        delete_response.raise_for_status()
        assert self._users_index_has_page_with_id(response1)
        assert not self._users_index_has_page_with_id(response2)
        assert self._users_index_has_page_with_id(response2, dict(deleted=True, show_published=False))

    def test_index_user_id_security(self):
        user_id = self.dataset_populator.user_id()
        response1 = self._create_valid_page_with_slug("indexuseridsecurity")
        assert self._users_index_has_page_with_id(response1, dict(user_id=user_id))
        with self._different_user():
            response = self._index_raw()
            assert response.status_code == 200
            response = self._index_raw(dict(user_id=user_id))
            assert response.status_code == 403

    def test_index_user_published(self):
        user_id = self.dataset_populator.user_id()
        response1 = self._create_valid_page_with_slug("indexuseridpublish1")
        with self._different_user():
            response2 = self._create_published_page_with_slug("indexuseridpublish2")
        assert self._users_index_has_page_with_id(response1)
        assert self._users_index_has_page_with_id(response2)
        assert self._users_index_has_page_with_id(response1, dict(user_id=user_id))
        assert not self._users_index_has_page_with_id(response2, dict(user_id=user_id))

    def test_index_show_published(self):
        with self._different_user():
            response = self._create_published_page_with_slug("indexshowpublish2")
        assert self._users_index_has_page_with_id(response)
        assert self._users_index_has_page_with_id(response, dict(show_published=True))
        assert not self._users_index_has_page_with_id(response, dict(show_published=False))

    def test_index_show_shared_with_me(self):
        user_id = self.dataset_populator.user_id()
        with self._different_user():
            response_published = self._create_published_page_with_slug("indexshowsharedpublished")
            response_shared = self._create_valid_page_with_slug("indexshowsharedshared")
            self._share_with_user(response_shared["id"], user_id)

        assert not self._users_index_has_page_with_id(response_shared)
        assert self._users_index_has_page_with_id(response_shared, dict(show_shared=True))
        assert not self._users_index_has_page_with_id(response_shared, dict(show_shared=False))
        # make sure published workflows still enabled by default...
        assert self._users_index_has_page_with_id(response_published, dict(show_shared=False))

    def test_index_show_shared_with_me_deleted(self):
        user_id = self.dataset_populator.user_id()
        with self._different_user():
            response_published = self._create_published_page_with_slug("indexshowsharedpublisheddeleted")
            response_shared = self._create_valid_page_with_slug("indexshowsharedshareddeleted")
            self._share_with_user(response_shared["id"], user_id)
            self._delete(f"pages/{response_published['id']}").raise_for_status()
            self._delete(f"pages/{response_shared['id']}").raise_for_status()

        assert not self._users_index_has_page_with_id(response_shared, dict(show_shared=True, show_published=True))
        assert not self._users_index_has_page_with_id(response_published, dict(show_shared=True, show_published=True))
        assert not self._users_index_has_page_with_id(response_shared, dict(show_published=True, deleted=True))
        assert not self._users_index_has_page_with_id(response_published, dict(show_published=True, deleted=True))

    def test_index_owner(self):
        my_workflow_id_1 = self._create_valid_page_with_slug("ownertags-m-1")
        email_1 = f"{uuid4()}@test.com"
        with self._different_user(email=email_1):
            published_page_id_1 = self._create_published_page_with_slug("ownertags-p-1")["id"]
            owner_1 = self._get("users").json()[0]["username"]

        email_2 = f"{uuid4()}@test.com"
        with self._different_user(email=email_2):
            published_page_id_2 = self._create_published_page_with_slug("ownertags-p-2")["id"]

        index_ids = self._index_ids(dict(search="is:published", show_published=True))
        assert published_page_id_1 in index_ids
        assert published_page_id_2 in index_ids
        assert my_workflow_id_1 not in index_ids

        index_ids = self._index_ids(dict(search=f"is:published u:{owner_1}", show_published=True))
        assert published_page_id_1 in index_ids
        assert published_page_id_2 not in index_ids
        assert my_workflow_id_1 not in index_ids

        index_ids = self._index_ids(dict(search=f"is:published u:'{owner_1}'", show_published=True))
        assert published_page_id_1 in index_ids
        assert published_page_id_2 not in index_ids
        assert my_workflow_id_1 not in index_ids

        index_ids = self._index_ids(dict(search=f"is:published {owner_1}", show_published=True))
        assert published_page_id_1 in index_ids
        assert published_page_id_2 not in index_ids
        assert my_workflow_id_1 not in index_ids

    def test_index_ordering(self):
        older1 = self._create_valid_page_with_slug(slug="indexorderingcreatedfirst", title="A PAGE")["id"]
        newer1 = self._create_valid_page_with_slug(slug="indexorderingcreatedsecond", title="B PAGE")["id"]
        index_ids = self._index_ids(dict(sort_desc=True))
        assert index_ids.index(older1) > index_ids.index(newer1)
        index_ids = self._index_ids()
        assert index_ids.index(older1) < index_ids.index(newer1)
        index_ids = self._index_ids(dict(sort_desc=False))  # the default but verify it works when explicit
        assert index_ids.index(older1) < index_ids.index(newer1)

        # update older1 so the update time is newer...
        revision_data = dict(content="<p>NewContent!</p>")
        self._post(f"pages/{older1}/revisions", data=revision_data).raise_for_status()
        index_ids = self._index_ids(dict(sort_desc=True))
        assert index_ids.index(older1) < index_ids.index(newer1)

        index_ids = self._index_ids(dict(sort_by="title", sort_desc=False))
        assert index_ids.index(older1) < index_ids.index(newer1)

    def test_index_limit_offset(self):
        older1 = self._create_valid_page_with_slug("indexlimitoffsetcreatedfirst")["id"]
        newer1 = self._create_valid_page_with_slug("indexlimitoffsetcreatedsecond")["id"]
        index_ids = self._index_ids(dict(limit=1, sort_desc=True))
        assert newer1 in index_ids
        assert older1 not in index_ids

        index_ids = self._index_ids(dict(limit=1, offset=1, sort_desc=True))
        assert newer1 not in index_ids
        assert older1 in index_ids

    def test_index_search_slug(self):
        response = self._create_valid_page_with_slug("indexsearchstringfoo")
        older1 = response["id"]
        newer1 = self._create_valid_page_with_slug("indexsearchstringbar")["id"]

        index_ids = self._index_ids(dict(search="slug:indexsearchstringfoo"))
        assert newer1 not in index_ids
        assert older1 in index_ids

        index_ids = self._index_ids(dict(search="slug:'indexsearchstringfoo'"))
        assert newer1 not in index_ids
        assert older1 in index_ids

        index_ids = self._index_ids(dict(search="slug:foo"))
        assert newer1 not in index_ids
        assert older1 in index_ids

        index_ids = self._index_ids(dict(search="foo"))
        assert newer1 not in index_ids
        assert older1 in index_ids

    def test_index_search_title(self):
        page_id = self._create_valid_page_with_slug("indexsearchbytitle", title="mycooltitle")["id"]
        assert page_id in self._index_ids(dict(search="mycooltitle"))
        assert page_id not in self._index_ids(dict(search="mycoolwrongtitle"))
        assert page_id in self._index_ids(dict(search="title:mycoolti"))
        assert page_id in self._index_ids(dict(search="title:'mycooltitle'"))
        assert page_id not in self._index_ids(dict(search="title:'mycoolti'"))

    def test_index_search_sharing_tags(self):
        user_id = self.dataset_populator.user_id()
        with self._different_user():
            response_published = self._create_valid_page_with_slug("indexshowsharedpublishedtags")["id"]
            self._make_public(response_published)
            response_shared = self._create_valid_page_with_slug("indexshowsharedsharedtags")["id"]
            self._share_with_user(response_shared, user_id)

        assert response_published in self._index_ids(dict(show_published=True, show_shared=True))
        assert response_shared in self._index_ids(dict(show_published=True, show_shared=True))

        assert response_published in self._index_ids(dict(show_published=True, show_shared=True, search="is:published"))
        assert response_shared not in self._index_ids(
            dict(show_published=True, show_shared=True, search="is:published")
        )

        assert response_published not in self._index_ids(
            dict(show_published=True, show_shared=True, search="is:shared_with_me")
        )
        assert response_shared in self._index_ids(
            dict(show_published=True, show_shared=True, search="is:shared_with_me")
        )

    def test_index_does_not_show_unavailable_pages(self):
        create_response_json = self._create_valid_page_as("others_page_index@bx.psu.edu", "otherspageindex")
        assert not self._users_index_has_page_with_id(create_response_json)

    def test_cannot_create_pages_with_same_slug(self):
        page_request = self._test_page_payload(slug="mypage1")
        page_response_1 = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response_1, 200)
        page_response_2 = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response_2, 400)
        self._assert_error_code_is(page_response_2, error_codes.error_codes_by_name["USER_SLUG_DUPLICATE"])

    def test_cannot_create_pages_with_invalid_slug(self):
        page_request = self._test_page_payload(slug="invalid slug!")
        page_response = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response, 400)

    def test_cannot_create_page_with_invalid_content_format(self):
        page_request = self._test_page_payload(slug="mypageinvalidformat")
        page_request["content_format"] = "xml"
        page_response_1 = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response_1, 400)
        self._assert_error_code_is(page_response_1, error_codes.error_codes_by_name["USER_REQUEST_INVALID_PARAMETER"])

    def test_page_requires_name(self):
        page_request = self._test_page_payload(slug="requires-name")
        del page_request["title"]
        page_response = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response, 400)
        self._assert_error_code_is(page_response, error_codes.error_codes_by_name["USER_REQUEST_MISSING_PARAMETER"])

    def test_page_requires_slug(self):
        page_request = self._test_page_payload()
        del page_request["slug"]
        page_response = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response, 400)

    def test_delete(self):
        response_json = self._create_valid_page_with_slug("testdelete")
        delete_response = delete(self._api_url(f"pages/{response_json['id']}", use_key=True))
        self._assert_status_code_is(delete_response, 204)

    def test_400_on_delete_invalid_page_id(self):
        delete_response = delete(self._api_url(f"pages/{self._random_key()}", use_key=True))
        self._assert_status_code_is(delete_response, 400)
        self._assert_error_code_is(delete_response, error_codes.error_codes_by_name["MALFORMED_ID"])

    def test_403_on_delete_unowned_page(self):
        page_response = self._create_valid_page_as("others_page@bx.psu.edu", "otherspage")
        delete_response = delete(self._api_url(f"pages/{page_response['id']}", use_key=True))
        self._assert_status_code_is(delete_response, 403)
        self._assert_error_code_is(delete_response, error_codes.error_codes_by_name["USER_DOES_NOT_OWN_ITEM"])

    def test_400_on_invalid_id_encoding(self):
        page_request = self._test_page_payload(slug="invalid-id-encding")
        page_request["content"] = """<p>Page!<div class="embedded-item" id="History-invaidencodedid"></div></p>"""
        page_response = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response, 400)
        self._assert_error_code_is(page_response, error_codes.error_codes_by_name["MALFORMED_ID"])

    def test_400_on_invalid_id_encoding_markdown(self):
        page_request = self._test_page_payload(slug="invalid-id-encding-markdown", content_format="markdown")
        page_request["content"] = """```galaxy\nhistory_dataset_display(history_dataset_id=badencoding)\n```\n"""
        page_response = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response, 400)
        self._assert_error_code_is(page_response, error_codes.error_codes_by_name["MALFORMED_ID"])

    def test_400_on_invalid_embedded_content(self):
        valid_id = self.dataset_populator.new_history()
        page_request = self._test_page_payload(slug="invalid-embed-content")
        page_request["content"] = f"""<p>Page!<div class="embedded-item" id="CoolObject-{valid_id}"></div></p>"""
        page_response = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response, 400)
        self._assert_error_code_is(page_response, error_codes.error_codes_by_name["USER_REQUEST_INVALID_PARAMETER"])
        assert "embedded HTML content" in page_response.text

    def test_400_on_invalid_markdown_call(self):
        page_request = self._test_page_payload(slug="invalid-markdown-call", content_format="markdown")
        page_request["content"] = """```galaxy\njob_metrics(job_id)\n```\n"""
        page_response = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response, 400)
        self._assert_error_code_is(page_response, error_codes.error_codes_by_name["MALFORMED_CONTENTS"])

    def test_show(self):
        response_json = self._create_valid_page_with_slug("pagetoshow")
        show_response = self._get(f"pages/{response_json['id']}")
        self._assert_status_code_is(show_response, 200)
        show_json = show_response.json()
        self._assert_has_keys(show_json, "slug", "title", "id")
        assert show_json["slug"] == "pagetoshow"
        assert show_json["title"] == "MY PAGE"
        assert show_json["content"] == "<p>Page!</p>"
        assert show_json["content_format"] == "html"

    def test_403_on_unowner_show(self):
        response_json = self._create_valid_page_as("others_page_show@bx.psu.edu", "otherspageshow")
        show_response = self._get(f"pages/{response_json['id']}")
        self._assert_status_code_is(show_response, 403)
        self._assert_error_code_is(show_response, error_codes.error_codes_by_name["USER_CANNOT_ACCESS_ITEM"])

    def test_501_on_download_pdf_when_service_unavailable(self):
        configuration = self.dataset_populator.get_configuration()
        can_produce_markdown = configuration["markdown_to_pdf_available"]
        if can_produce_markdown:
            raise SkipTest("Skipping test because server does implement markdown conversion to PDF")
        page_request = self._test_page_payload(slug="md-page-to-pdf-not-implemented", content_format="markdown")
        page_response = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response, 200)
        page_id = page_response.json()["id"]
        pdf_response = self._get(f"pages/{page_id}.pdf")
        api_asserts.assert_status_code_is(pdf_response, 501)
        api_asserts.assert_error_code_is(
            pdf_response, error_codes.error_codes_by_name["SERVER_NOT_CONFIGURED_FOR_REQUEST"]
        )

    def test_pdf_when_service_available(self):
        configuration = self.dataset_populator.get_configuration()
        can_produce_markdown = configuration["markdown_to_pdf_available"]
        if not can_produce_markdown:
            raise SkipTest("Skipping test because server does not implement markdown conversion to PDF")
        page_request = self._test_page_payload(slug="md-page-to-pdf", content_format="markdown")
        page_response = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response, 200)
        page_id = page_response.json()["id"]
        pdf_response = self._get(f"pages/{page_id}.pdf")
        api_asserts.assert_status_code_is(pdf_response, 200)
        assert "application/pdf" in pdf_response.headers["content-type"]
        assert pdf_response.content[0:4] == b"%PDF"

    def test_400_on_download_pdf_when_unsupported_content_format(self):
        page_request = self._test_page_payload(slug="html-page-to-pdf", content_format="html")
        page_response = self._post("pages", page_request, json=True)
        self._assert_status_code_is(page_response, 200)
        page_id = page_response.json()["id"]
        pdf_response = self._get(f"pages/{page_id}.pdf")
        self._assert_status_code_is(pdf_response, 400)

    def _create_published_page_with_slug(self, slug, **kwd) -> Dict[str, Any]:
        response = self.dataset_populator.new_page(slug=slug, **kwd)
        response = self._make_public(response["id"])
        return response

    def _make_public(self, page_id: str) -> dict:
        return self.dataset_populator.make_page_public(page_id)

    def _share_with_user(self, page_id: str, user_id_or_email: str):
        data = {"user_ids": [user_id_or_email]}
        response = self._put(f"pages/{page_id}/share_with_users", data, json=True)
        api_asserts.assert_status_code_is_ok(response)

    def _index_raw(self, params: Optional[Dict[str, Any]] = None) -> Response:
        index_response = self._get("pages", data=params or {})
        return index_response

    def _index(self, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        index_response = self._index_raw(params)
        self._assert_status_code_is(index_response, 200)
        return index_response.json()

    def _index_ids(self, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [p["id"] for p in self._index(params)]

    def _users_index_has_page_with_id(
        self, has_id: Union[Dict[str, Any], str], params: Optional[Dict[str, Any]] = None
    ):
        pages = self._index(params)
        if isinstance(has_id, dict):
            target_id = has_id["id"]
        else:
            target_id = has_id
        return target_id in (_["id"] for _ in pages)

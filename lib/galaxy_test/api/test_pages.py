from requests import delete

from galaxy.exceptions import error_codes
from galaxy_test.base.populators import DatasetPopulator, skip_without_tool, WorkflowPopulator
from ._framework import ApiTestCase


class BasePageApiTestCase(ApiTestCase):

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
        content_format = kwds.get("content_format", "html")
        if content_format == "html":
            content = "<p>Page!</p>"
        else:
            content = "*Page*\n\n"
        request = dict(
            slug="mypage",
            title="MY PAGE",
            content=content,
            content_format=content_format,
        )
        request.update(**kwds)
        return request


class PageApiTestCase(BasePageApiTestCase):

    def test_create(self):
        response_json = self._create_valid_page_with_slug("mypage")
        self._assert_has_keys(response_json, "slug", "title", "id")

    @skip_without_tool("cat")
    def test_create_from_report(self):
        dataset_populator = DatasetPopulator(self.galaxy_interactor)
        workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        test_data = """
input_1:
  value: 1.bed
  type: File
"""
        with dataset_populator.test_history() as history_id:
            summary = workflow_populator.run_workflow("""
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
""", test_data=test_data, history_id=history_id)

            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            report_json = workflow_populator.workflow_report_json(workflow_id, invocation_id)
            assert "markdown" in report_json
            self._assert_has_keys(report_json , "markdown", "render_format")
            assert report_json["render_format"] == "markdown"
            markdown_content = report_json["markdown"]
            page_request = dict(
                slug="invocation-report",
                title="Invocation Report",
                invocation_id=invocation_id,
            )
            page_response = self._post("pages", page_request)
            self._assert_status_code_is(page_response, 200)
            page_response = page_response.json()
            show_response = self._get("pages/%s" % page_response['id'])
            self._assert_status_code_is(show_response, 200)
            show_json = show_response.json()
            self._assert_has_keys(show_json, "slug", "title", "id")
            self.assertEqual(show_json["slug"], "invocation-report")
            self.assertEqual(show_json["title"], "Invocation Report")
            self.assertEqual(show_json["content_format"], "markdown")
            markdown_content = show_json["content"]
            assert "## Workflow Outputs" in markdown_content
            assert "## Workflow Inputs" in markdown_content
            assert "## About This Report" not in markdown_content

    def test_index(self):
        create_response_json = self._create_valid_page_with_slug("indexpage")
        assert self._users_index_has_page_with_id(create_response_json["id"])

    def test_index_does_not_show_unavailable_pages(self):
        create_response_json = self._create_valid_page_as("others_page_index@bx.psu.edu", "otherspageindex")
        assert not self._users_index_has_page_with_id(create_response_json["id"])

    def test_cannot_create_pages_with_same_slug(self):
        page_request = self._test_page_payload(slug="mypage1")
        page_response_1 = self._post("pages", page_request)
        self._assert_status_code_is(page_response_1, 200)
        page_response_2 = self._post("pages", page_request)
        self._assert_status_code_is(page_response_2, 400)
        self._assert_error_code_is(page_response_2, error_codes.USER_SLUG_DUPLICATE)

    def test_cannot_create_page_with_invalid_content_format(self):
        page_request = self._test_page_payload(slug="mypageinvalidformat")
        page_request["content_format"] = "xml"
        page_response_1 = self._post("pages", page_request)
        self._assert_status_code_is(page_response_1, 400)
        self._assert_error_code_is(page_response_1, error_codes.USER_REQUEST_INVALID_PARAMETER)

    def test_page_requires_name(self):
        page_request = self._test_page_payload(slug="requires-name")
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

    def test_400_on_delete_invalid_page_id(self):
        delete_response = delete(self._api_url("pages/%s" % self._random_key(), use_key=True))
        self._assert_status_code_is(delete_response, 400)
        self._assert_error_code_is(delete_response, error_codes.MALFORMED_ID)

    def test_403_on_delete_unowned_page(self):
        page_response = self._create_valid_page_as("others_page@bx.psu.edu", "otherspage")
        delete_response = delete(self._api_url("pages/%s" % page_response["id"], use_key=True))
        self._assert_status_code_is(delete_response, 403)
        self._assert_error_code_is(delete_response, error_codes.USER_DOES_NOT_OWN_ITEM)

    def test_400_on_invalid_id_encoding(self):
        page_request = self._test_page_payload(slug="invalid-id-encding")
        page_request["content"] = '''<p>Page!<div class="embedded-item" id="History-invaidencodedid"></div></p>'''
        page_response = self._post("pages", page_request)
        self._assert_status_code_is(page_response, 400)
        self._assert_error_code_is(page_response, error_codes.MALFORMED_ID)

    def test_400_on_invalid_id_encoding_markdown(self):
        page_request = self._test_page_payload(slug="invalid-id-encding-markdown", content_format="markdown")
        page_request["content"] = '''```galaxy\nhistory_dataset_display(history_dataset_id=badencoding)\n```\n'''
        page_response = self._post("pages", page_request)
        self._assert_status_code_is(page_response, 400)
        self._assert_error_code_is(page_response, error_codes.MALFORMED_ID)

    def test_400_on_invalid_embedded_content(self):
        dataset_populator = DatasetPopulator(self.galaxy_interactor)
        valid_id = dataset_populator.new_history()
        page_request = self._test_page_payload(slug="invalid-embed-content")
        page_request["content"] = '''<p>Page!<div class="embedded-item" id="CoolObject-%s"></div></p>''' % valid_id
        page_response = self._post("pages", page_request)
        self._assert_status_code_is(page_response, 400)
        self._assert_error_code_is(page_response, error_codes.USER_REQUEST_INVALID_PARAMETER)
        assert "embedded HTML content" in page_response.text

    def test_400_on_invalid_markdown_call(self):
        page_request = self._test_page_payload(slug="invalid-markdown-call", content_format="markdown")
        page_request["content"] = '''```galaxy\njob_metrics(job_id)\n```\n'''
        page_response = self._post("pages", page_request)
        self._assert_status_code_is(page_response, 400)
        self._assert_error_code_is(page_response, error_codes.MALFORMED_CONTENTS)

    def test_show(self):
        response_json = self._create_valid_page_with_slug("pagetoshow")
        show_response = self._get("pages/%s" % response_json['id'])
        self._assert_status_code_is(show_response, 200)
        show_json = show_response.json()
        self._assert_has_keys(show_json, "slug", "title", "id")
        self.assertEqual(show_json["slug"], "pagetoshow")
        self.assertEqual(show_json["title"], "MY PAGE")
        self.assertEqual(show_json["content"], "<p>Page!</p>")
        self.assertEqual(show_json["content_format"], "html")

    def test_403_on_unowner_show(self):
        response_json = self._create_valid_page_as("others_page_show@bx.psu.edu", "otherspageshow")
        show_response = self._get("pages/%s" % response_json['id'])
        self._assert_status_code_is(show_response, 403)
        self._assert_error_code_is(show_response, error_codes.USER_CANNOT_ACCESS_ITEM)

    def _users_index_has_page_with_id(self, id):
        index_response = self._get("pages")
        self._assert_status_code_is(index_response, 200)
        pages = index_response.json()
        return id in (_["id"] for _ in pages)

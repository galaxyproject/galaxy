"""Test pages save JSON with unencoded IDs.

Verifies the database doesn't get saved with encoded IDs (that would be bad because
the security parameter to encode IDs may be changed by admins). Test case also verifies
exported API values are encoded though.
"""

from galaxy import model
from galaxy_test.base import api_asserts
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class PageJsonEncodingIntegrationTestCase(integration_util.IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    def test_page_encoding(self):
        request = dict(
            slug="mypage",
            title="MY PAGE",
            content="""<p>Page!<div class="embedded-item" id="History-%s"></div></p>""" % self.history_id,
        )
        page_response = self._post("pages", request, json=True)
        api_asserts.assert_status_code_is_ok(page_response)
        sa_session = self._app.model.context
        page_revision = sa_session.query(model.PageRevision).filter_by(content_format="html").all()[0]
        assert '''id="History-1"''' in page_revision.content, page_revision.content
        assert '''id="History-%s"''' % self.history_id not in page_revision.content, page_revision.content

        show_page_response = self._get("pages/%s" % page_response.json()["id"])
        api_asserts.assert_status_code_is_ok(show_page_response)
        content = show_page_response.json()["content"]
        assert '''id="History-1"''' not in content, content
        assert '''id="History-%s"''' % self.history_id in content, content

    def test_page_encoding_markdown(self):
        dataset = self.dataset_populator.new_dataset(self.history_id)
        dataset_id = dataset["id"]
        request = dict(
            slug="mypage-markdown",
            title="MY PAGE",
            content="""```galaxy
history_dataset_display(history_dataset_id=%s)
```"""
            % dataset["id"],
            content_format="markdown",
        )
        page_response = self._post("pages", request, json=True)
        api_asserts.assert_status_code_is_ok(page_response)
        sa_session = self._app.model.context
        page_revision = sa_session.query(model.PageRevision).filter_by(content_format="markdown").all()[0]
        assert (
            """```galaxy
history_dataset_display(history_dataset_id=1)
```"""
            in page_revision.content
        ), page_revision.content
        assert (
            """::: history_dataset_display history_dataset_id=%s""" % dataset_id not in page_revision.content
        ), page_revision.content

        show_page_response = self._get("pages/%s" % page_response.json()["id"])
        api_asserts.assert_status_code_is_ok(show_page_response)
        content = show_page_response.json()["content"]
        assert (
            """```galaxy
history_dataset_display(history_dataset_id=1)
```"""
            not in content
        ), content
        assert (
            """```galaxy
history_dataset_display(history_dataset_id=%s)
```"""
            % dataset_id
            in content
        ), content

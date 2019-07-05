"""Test pages save JSON with unencoded IDs.

Verifies the database doesn't get saved with encoded IDs (that would be bad because
the security parameter to encode IDs may be changed by admins). Test case also verifies
exported API values are encoded though.
"""

from base import api_asserts
from base import integration_util
from base.populators import (
    DatasetPopulator,
)
from galaxy import model  # noqa: I101,I201


class PageJsonEncodingIntegrationTestCase(integration_util.IntegrationTestCase):

    def setUp(self):
        super(PageJsonEncodingIntegrationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_page_encoding(self):
        history_id = self.dataset_populator.new_history()
        request = dict(
            slug="mypage",
            title="MY PAGE",
            content='''<p>Page!<div class="embedded-item" id="History-%s"></div></p>''' % history_id,
        )
        page_response = self._post("pages", request)
        api_asserts.assert_status_code_is_ok(page_response)
        sa_session = self._app.model.context
        page_revision = sa_session.query(model.PageRevision).all()[0]
        assert '''id="History-1"''' in page_revision.content, page_revision.content
        assert '''id="History-%s"''' % history_id not in page_revision.content, page_revision.content

        show_page_response = self._get("pages/%s" % page_response.json()["id"])
        api_asserts.assert_status_code_is_ok(show_page_response)
        content = show_page_response.json()["content"]
        assert '''id="History-1"''' not in content, content
        assert '''id="History-%s"''' % history_id in content, content

"""Test pages save JSON with unencoded IDs.

Verifies the database doesn't get saved with encoded IDs (that would be bad because
the security parameter to encode IDs may be changed by admins). Test case also verifies
exported API values are encoded though.
"""

import re

from sqlalchemy import select

from galaxy import model
from galaxy_test.base import api_asserts
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class TestPageJsonEncodingIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_page_encoding(self, history_id: str):
        history_num_re = re.compile(r'id="History-\d+"')
        request = dict(
            slug="mypage",
            title="MY PAGE",
            content=f"""<p>Page!<div class="embedded-item" id="History-{history_id}"></div></p>""",
        )
        page_response = self._post("pages", request, json=True)
        api_asserts.assert_status_code_is_ok(page_response)
        sa_session = self._app.model.session
        page_revision = sa_session.scalars(select(model.PageRevision).filter_by(content_format="html")).all()[0]
        assert history_num_re.search(page_revision.content), page_revision.content
        assert f'''id="History-{history_id}"''' not in page_revision.content, page_revision.content

        show_page_response = self._get("pages/{}".format(page_response.json()["id"]))
        api_asserts.assert_status_code_is_ok(show_page_response)
        content = show_page_response.json()["content"]
        assert not history_num_re.search(content), content
        assert f'''id="History-{history_id}"''' in content, content

    def test_page_encoding_markdown(self, history_id: str):
        dataset = self.dataset_populator.new_dataset(history_id)
        dataset_id = dataset["id"]
        request = dict(
            slug="mypage-markdown",
            title="MY PAGE",
            content="""```galaxy
history_dataset_display(history_dataset_id={})
```""".format(
                dataset["id"]
            ),
            content_format="markdown",
        )
        page_response = self._post("pages", request, json=True)
        api_asserts.assert_status_code_is_ok(page_response)
        sa_session = self._app.model.session
        page_revision = sa_session.scalars(select(model.PageRevision).filter_by(content_format="markdown")).all()[0]
        assert (
            """```galaxy
history_dataset_display(history_dataset_id=1)
```"""
            in page_revision.content
        ), page_revision.content
        assert (
            f"""::: history_dataset_display history_dataset_id={dataset_id}""" not in page_revision.content
        ), page_revision.content

        show_page_response = self._get("pages/{}".format(page_response.json()["id"]))
        api_asserts.assert_status_code_is_ok(show_page_response)
        content = show_page_response.json()["content"]
        assert (
            """```galaxy
history_dataset_display(history_dataset_id=1)
```"""
            not in content
        ), content
        assert (
            f"""```galaxy
history_dataset_display(history_dataset_id={dataset_id})
```"""
            in content
        ), content

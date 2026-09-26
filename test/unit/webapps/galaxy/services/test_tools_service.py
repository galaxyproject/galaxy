from typing import (
    Any,
    cast,
)
from unittest.mock import Mock

from galaxy.app_unittest_utils import galaxy_mock
from galaxy.files import (
    ConfiguredFileSources,
    ConfiguredFileSourcesConf,
)
from galaxy.files.models import FileSourcePluginsConfig
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.model import History
from galaxy.schema.fetch_data import FetchDataPayload
from galaxy.schema.fields import Security
from galaxy.webapps.galaxy.services.tools import ToolsService


class _ToolsServiceUnderTest(ToolsService):
    def _create(self, trans, payload, **kwd):
        return payload


class TestToolsService:
    def setup_method(self):
        self.trans = galaxy_mock.MockTrans()
        self.app = self.trans.app
        Security.security = self.app.security
        self.app.config.check_upload_content = True
        self.authnz_manager = Mock()
        self.app.authnz_manager = self.authnz_manager
        self.trans.init_user_in_database()
        history = History(user=self.trans.user)
        self.trans.sa_session.add(history)
        self.trans.sa_session.commit()
        self.trans.set_history(history)

    def _service(self):
        return _ToolsServiceUnderTest(
            config=self.app.config,
            toolbox_search=cast(Any, object()),
            security=self.app.security,
            history_manager=cast(Any, object()),
        )

    def test_tool_lookup_only_materializes_at_explicit_boundary(self):
        toolbox = Mock()
        cast(Any, self.app).toolbox = toolbox
        tool = Mock()
        tool.allow_user_access.return_value = True
        toolbox.get_tool = Mock(return_value=tool)
        toolbox.materialize_tool = Mock(return_value="parsed")
        service = self._service()

        assert service._get_tool(self.trans, "cat1", user=self.trans.user) is tool
        toolbox.materialize_tool.assert_not_called()

        assert (
            service._get_materialized_tool(self.trans, "cat1", user=self.trans.user, materialization_reason="detail")
            == "parsed"
        )
        toolbox.materialize_tool.assert_called_once_with(tool, reason="detail")

    def test_create_fetch_does_not_refresh_when_fetch_has_no_authorization_header(self):
        self.app.file_sources = ConfiguredFileSources(
            FileSourcePluginsConfig(),
            ConfiguredFileSourcesConf(
                conf_dict=[
                    {
                        "type": "http",
                        "id": "test_plain",
                        "url_regex": r"^https?://example\.org/",
                    }
                ]
            ),
        )

        service = self._service()
        payload = FetchDataPayload.model_validate(
            {
                "history_id": self.app.security.encode_id(self.trans.history.id),
                "targets": [
                    {
                        "destination": {"type": "hdas"},
                        "elements": [
                            {
                                "src": "url",
                                "url": "https://example.org/data.txt",
                                "ext": "txt",
                            }
                        ],
                    }
                ],
            }
        )

        service.create_fetch(cast(ProvidesHistoryContext, self.trans), payload)
        cast(Mock, self.authnz_manager.refresh_expiring_oidc_tokens).assert_not_called()

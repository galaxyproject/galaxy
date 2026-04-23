from datetime import (
    UTC,
    datetime,
    timedelta,
)
from unittest.mock import Mock

from galaxy.app_unittest_utils import galaxy_mock
from galaxy.files import (
    ConfiguredFileSources,
    ConfiguredFileSourcesConf,
    FileSourcePluginsConfig,
)
from galaxy.model import (
    History,
    UserAuthnzToken,
)
from galaxy.schema.fetch_data import FetchDataPayload
from galaxy.schema.fields import Security
from galaxy.webapps.galaxy.services.tools import ToolsService


class TestToolsService:
    def setup_method(self):
        self.trans = galaxy_mock.MockTrans()
        self.app = self.trans.app
        Security.security = self.app.security
        self.app.config.check_upload_content = True
        self.trans.init_user_in_database()
        history = History(user=self.trans.user)
        self.trans.sa_session.add(history)
        self.trans.sa_session.commit()
        self.trans.set_history(history)

    def test_create_fetch_stages_token_expiration_input(self):
        self.app.file_sources = ConfiguredFileSources(
            FileSourcePluginsConfig(),
            ConfiguredFileSourcesConf(
                conf_dict=[
                    {
                        "type": "http",
                        "id": "test_oidc",
                        "url_regex": r"^https?://example\.org/",
                        "http_headers": {
                            "Authorization": "Bearer ${user.oidc_access_tokens['oidc']}",
                        },
                    }
                ]
            ),
        )
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        token = UserAuthnzToken(
            provider="oidc",
            uid="oidc-user",
            user=self.trans.user,
            extra_data={"access_token": "access-token"},
        )
        token.expiration_time = expires_at
        self.trans.sa_session.add(token)
        self.trans.sa_session.commit()

        service = ToolsService(
            config=self.app.config,
            toolbox_search=Mock(),
            security=self.app.security,
            history_manager=Mock(),
        )
        service._create = Mock(side_effect=lambda trans, payload, **kwd: payload)

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
        create_payload = service.create_fetch(self.trans, payload)

        assert create_payload["tool_id"] == "__DATA_FETCH__"
        assert create_payload["inputs"]["token_expires_at"] == expires_at.isoformat()

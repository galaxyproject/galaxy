from datetime import (
    datetime,
    timedelta,
    timezone,
)
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
from galaxy.model import (
    History,
    User,
    UserAuthnzToken,
)
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
        auth_time = datetime.now(timezone.utc)
        expires_at = auth_time + timedelta(hours=1)
        token = UserAuthnzToken(
            provider="oidc",
            uid="oidc-user",
            user=cast(User, self.trans.user),
            extra_data={
                "access_token": "access-token",
                "auth_time": int(auth_time.timestamp()),
                "expires": int(timedelta(hours=1).total_seconds()),
            },
        )
        self.trans.sa_session.add(token)
        self.trans.sa_session.commit()

        service = _ToolsServiceUnderTest(
            config=self.app.config,
            toolbox_search=cast(Any, object()),
            security=self.app.security,
            history_manager=cast(Any, object()),
        )

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
        create_payload = service.create_fetch(cast(ProvidesHistoryContext, self.trans), payload)

        assert create_payload["tool_id"] == "__DATA_FETCH__"
        assert create_payload["inputs"]["token_expires_at"] == expires_at.replace(microsecond=0).isoformat()
        cast(Mock, self.authnz_manager.refresh_expiring_oidc_tokens).assert_called_once_with(
            self.trans, self.trans.user
        )

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

        service = _ToolsServiceUnderTest(
            config=self.app.config,
            toolbox_search=cast(Any, object()),
            security=self.app.security,
            history_manager=cast(Any, object()),
        )
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

        create_payload = service.create_fetch(cast(ProvidesHistoryContext, self.trans), payload)

        assert "token_expires_at" not in create_payload["inputs"]
        cast(Mock, self.authnz_manager.refresh_expiring_oidc_tokens).assert_not_called()

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import (
    Any,
    cast,
)

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


class TestableToolsService(ToolsService):
    def _create(self, trans, payload, **kwd):
        return payload


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
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        token = UserAuthnzToken(
            provider="oidc",
            uid="oidc-user",
            user=cast(User, self.trans.user),
            extra_data={"access_token": "access-token"},
        )
        cast(Any, token).expiration_time = expires_at
        self.trans.sa_session.add(token)
        self.trans.sa_session.commit()

        service = TestableToolsService(
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
        assert create_payload["inputs"]["token_expires_at"] == expires_at.isoformat()

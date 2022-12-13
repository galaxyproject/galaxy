from typing import (
    Optional,
    TYPE_CHECKING,
)

from galaxy.model import User
from galaxy.structured_app import BasicSharedApp

if TYPE_CHECKING:
    from galaxy.model import APIKeys


class ApiKeyManager:
    def __init__(self, app: BasicSharedApp):
        self.app = app

    def get_api_key(self, user: User) -> Optional["APIKeys"]:
        sa_session = self.app.model.context
        api_key = (
            sa_session.query(self.app.model.APIKeys)
            .filter_by(user_id=user.id, deleted=False)
            .order_by(self.app.model.APIKeys.create_time.desc())
            .first()
        )
        return api_key

    def create_api_key(self, user: User) -> "APIKeys":
        guid = self.app.security.get_new_guid()
        new_key = self.app.model.APIKeys()
        new_key.user_id = user.id
        new_key.key = guid
        sa_session = self.app.model.context
        sa_session.add(new_key)
        sa_session.flush()
        return new_key

    def get_or_create_api_key(self, user: User) -> str:
        # Logic Galaxy has always used - but it would appear to have a race
        # condition. Worth fixing? Would kind of need a message queue to fix
        # in multiple process mode.
        api_key = self.get_api_key(user)
        key = api_key.key if api_key else self.create_api_key(user).key
        return key

    def delete_api_key(self, user: User) -> None:
        """Marks the current user API key as deleted."""
        sa_session = self.app.model.context
        # Before it was possible to create multiple API keys for the same user although they were not considered valid
        # So all non-deleted keys are marked as deleted for backward compatibility
        api_keys = sa_session.query(self.app.model.APIKeys).filter_by(user_id=user.id, deleted=False)
        for api_key in api_keys:
            api_key.deleted = True
            sa_session.add(api_key)
        sa_session.flush()

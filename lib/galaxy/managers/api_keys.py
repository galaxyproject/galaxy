from sqlalchemy import (
    false,
    select,
    update,
)
from typing_extensions import Protocol

from galaxy.structured_app import BasicSharedApp


class IsUserModel(Protocol):
    id: int


class ApiKeyManager:
    def __init__(self, app: BasicSharedApp):
        self.app = app
        self.session = self.app.model.context

    def get_api_key(self, user: IsUserModel):
        APIKeys = self.app.model.APIKeys
        stmt = select(APIKeys).filter_by(user_id=user.id, deleted=False).order_by(APIKeys.create_time.desc()).limit(1)
        return self.session.scalars(stmt).first()

    def create_api_key(self, user: IsUserModel):
        guid = self.app.security.get_new_guid()
        new_key = self.app.model.APIKeys()
        new_key.user_id = user.id
        new_key.key = guid
        self.session.add(new_key)
        self.session.commit()
        return new_key

    def get_or_create_api_key(self, user: IsUserModel) -> str:
        # Logic Galaxy has always used - but it would appear to have a race
        # condition. Worth fixing? Would kind of need a message queue to fix
        # in multiple process mode.
        api_key = self.get_api_key(user)
        key = api_key.key if api_key else self.create_api_key(user).key
        return key

    def delete_api_key(self, user: IsUserModel) -> None:
        """Marks the current user API key as deleted."""
        # Before it was possible to create multiple API keys for the same user although they were not considered valid
        # So all non-deleted keys are marked as deleted for backward compatibility
        self._mark_all_api_keys_as_deleted(user.id)
        self.session.commit()

    def _mark_all_api_keys_as_deleted(self, user_id: int):
        APIKeys = self.app.model.APIKeys
        stmt = (
            update(APIKeys)
            .where(APIKeys.user_id == user_id)
            .where(APIKeys.deleted == false())
            .values(deleted=True)
            .execution_options(synchronize_session="evaluate")
        )
        return self.session.execute(stmt)

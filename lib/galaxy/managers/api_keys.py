from typing import List

from galaxy.model import (
    APIKeys,
    User,
)
from galaxy.structured_app import BasicSharedApp


class ApiKeyManager:
    def __init__(self, app: BasicSharedApp):
        self.app = app

    def get_api_keys(self, user: User) -> List[APIKeys]:
        return user.api_keys

    def create_api_key(self, user: User) -> APIKeys:
        guid = self.app.security.get_new_guid()
        new_key = APIKeys()
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
        if user.api_keys:
            key = user.api_keys[0].key
        else:
            key = self.create_api_key(user).key
        return key

    def delete_api_key(self, user: User, key: str) -> None:
        sa_session = self.app.model.context
        sa_session.query(APIKeys).filter_by(user_id=user.id, key=key).delete()
        sa_session.flush()

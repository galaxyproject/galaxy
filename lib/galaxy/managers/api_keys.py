from typing import List

from galaxy.model import APIKeys
from galaxy.structured_app import BasicSharedApp


class ApiKeyManager:
    def __init__(self, app: BasicSharedApp):
        self.app = app

    def get_api_keys(self, user) -> List[APIKeys]:
        return user.api_keys

    def create_api_key(self, user) -> APIKeys:
        guid = self.app.security.get_new_guid()
        new_key = self.app.model.APIKeys()
        new_key.user_id = user.id
        new_key.key = guid
        sa_session = self.app.model.context
        sa_session.add(new_key)
        sa_session.flush()
        return new_key

    def get_or_create_api_key(self, user) -> str:
        # Logic Galaxy has always used - but it would appear to have a race
        # condition. Worth fixing? Would kind of need a message queue to fix
        # in multiple process mode.
        if user.api_keys:
            key = user.api_keys[0].key
        else:
            key = self.create_api_key(user).key
        return key

    def delete_api_key(self, user, key) -> None:
        sa_session = self.app.model.context
        sa_session.query(self.app.model.APIKeys).filter_by(user_id=user.id, key=key).delete()
        sa_session.flush()

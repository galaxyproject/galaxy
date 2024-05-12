from typing import (
    Generic,
    Optional,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from sqlalchemy import (
    false,
    select,
    update,
)

from galaxy.model.base import transaction
from galaxy.structured_app import BasicSharedApp

if TYPE_CHECKING:
    from galaxy.model import (
        APIKeys as GalaxyAPIKeys,
        User as GalaxyUser,
    )
    from tool_shed.webapp.model import (
        APIKeys as ToolShedAPIKeys,
        User as ToolShedUser,
    )

A = TypeVar("A", bound=Union["GalaxyAPIKeys", "ToolShedAPIKeys"])
U = TypeVar("U", bound=Union["GalaxyUser", "ToolShedUser"])


class ApiKeyManager(Generic[A, U]):
    def __init__(self, app: BasicSharedApp):
        self.app = app
        self.session = self.app.model.context

    def get_api_key(self, user: U) -> Optional[A]:
        APIKeys = self.app.model.APIKeys
        stmt = select(APIKeys).filter_by(user_id=user.id, deleted=False).order_by(APIKeys.create_time.desc()).limit(1)
        return self.session.scalars(stmt).first()

    def create_api_key(self, user: U) -> A:
        guid = self.app.security.get_new_guid()
        new_key = self.app.model.APIKeys()
        new_key.user_id = user.id
        new_key.key = guid
        self.session.add(new_key)
        with transaction(self.session):
            self.session.commit()
        return new_key

    def get_or_create_api_key(self, user: U) -> str:
        # Logic Galaxy has always used - but it would appear to have a race
        # condition. Worth fixing? Would kind of need a message queue to fix
        # in multiple process mode.
        api_key = self.get_api_key(user)
        key = api_key.key if api_key else self.create_api_key(user).key
        assert key
        return key

    def delete_api_key(self, user: U) -> None:
        """Marks the current user API key as deleted."""
        # Before it was possible to create multiple API keys for the same user although they were not considered valid
        # So all non-deleted keys are marked as deleted for backward compatibility
        self._mark_all_api_keys_as_deleted(user.id)
        with transaction(self.session):
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

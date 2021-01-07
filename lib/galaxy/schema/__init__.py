import typing

from pydantic import BaseModel


class BootstrapAdminUser(BaseModel):
    id = 0
    email: typing.Optional[str] = None
    preferences: typing.Dict[str, str] = {}
    bootstrap_admin_user = True

    def all_roles(*args) -> list:
        return []

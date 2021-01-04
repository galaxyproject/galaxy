import typing

from pydantic import BaseModel


class BoostrapAdminUser(BaseModel):
    id = 0
    email: typing.Optional[str] = None
    bootstrap_admin_user = True

    def all_roles(*args) -> list:
        return []

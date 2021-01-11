from typing import (
    Dict,
    Optional,
)

from pydantic import BaseModel


class BootstrapAdminUser(BaseModel):
    id = 0
    email: Optional[str] = None
    preferences: Dict[str, str] = {}
    bootstrap_admin_user = True

    def all_roles(*args) -> list:
        return []

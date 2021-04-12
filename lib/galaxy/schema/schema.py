from datetime import datetime

from pydantic import (
    BaseModel,
    Field,
)

from galaxy.schema.fields import (
    EncodedDatabaseIdField,
    ModelClassField,
)

USER_MODEL_CLASS_NAME = "User"


class UserModel(BaseModel):
    """User in a transaction context."""
    id: EncodedDatabaseIdField = Field(title='ID', description='User ID')
    username: str = Field(title='Username', description='User username')
    email: str = Field(title='Email', description='User email')
    active: bool = Field(title='Active', description='User is active')
    deleted: bool = Field(title='Deleted', description='User is deleted')
    last_password_change: datetime = Field(title='Last password change', description='')
    model_class: str = ModelClassField(USER_MODEL_CLASS_NAME)


from galaxy.schema.schema import UserUpdatePayload
from galaxy.webapps.galaxy.api.users import (
    ACCOUNT_IDENTITY_FIELDS,
    ACCOUNT_INTERFACE_EXEMPT_FIELDS,
)


def test_every_update_payload_field_is_classified_for_the_account_interface_gate():
    assert ACCOUNT_IDENTITY_FIELDS.isdisjoint(ACCOUNT_INTERFACE_EXEMPT_FIELDS)
    assert set(UserUpdatePayload.model_fields) == ACCOUNT_IDENTITY_FIELDS | ACCOUNT_INTERFACE_EXEMPT_FIELDS

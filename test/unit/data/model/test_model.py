from uuid import (
    UUID,
    uuid4,
)

from galaxy import model


def test_get_uuid():
    my_uuid = uuid4()
    rval = model.get_uuid(my_uuid)
    assert rval == UUID(str(my_uuid))

    rval = model.get_uuid()
    assert isinstance(rval, UUID)


def test_permitted_actions():
    actions = model.Dataset.permitted_actions
    assert actions and len(actions.values()) == 2

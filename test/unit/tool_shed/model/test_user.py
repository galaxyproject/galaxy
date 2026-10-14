import pytest
from sqlalchemy.exc import IntegrityError

from tool_shed.webapp.model import User
from .._util import TestToolShedApp


def test_username_is_unique(shed_app: TestToolShedApp):
    session = shed_app.model.context
    session.add(User(email="a@galaxyproject.org", username="taken", password="x"))
    session.add(User(email="b@galaxyproject.org", username="taken", password="x"))
    with pytest.raises(IntegrityError):
        session.flush()

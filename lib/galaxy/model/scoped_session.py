"""
These classes are used for registering different scoped_session objects with
the DI framework. This type distinction is necessary because we need to store
scoped_session objects that produce sessions that may have different binds
(i.e., if the tool_shed_install model uses a different database).
"""

from sqlalchemy.orm import scoped_session


class galaxy_scoped_session(scoped_session):
    """scoped_session used for galaxy model."""


class install_model_scoped_session(scoped_session):
    """scoped_session used for tool_shed_install model."""

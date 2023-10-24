from sqlalchemy import select

from galaxy.model import (
    FormDefinition,
    FormDefinitionCurrent,
)


def get_form_definitions(session):
    stmt = select(FormDefinition)
    return session.scalars(stmt)


def get_form_definitions_current(session):
    stmt = select(FormDefinitionCurrent)
    return session.scalars(stmt)


def get_filtered_form_definitions_current(session, filter):
    stmt = select(FormDefinitionCurrent).filter_by(**filter)
    return session.scalars(stmt)

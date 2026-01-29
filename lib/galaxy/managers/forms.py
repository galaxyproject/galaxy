from sqlalchemy import select
from sqlalchemy.exc import (
    MultipleResultsFound,
    NoResultFound,
)

from galaxy.exceptions import (
    InconsistentDatabase,
    InternalServerError,
    RequestParameterInvalidException,
)
from galaxy.managers import base
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import (
    FormDefinition,
    FormDefinitionCurrent,
)
from galaxy.util import unicodify


def get_form_definitions(session):
    stmt = select(FormDefinition)
    return session.scalars(stmt)


def get_form_definitions_current(session):
    stmt = select(FormDefinitionCurrent)
    return session.scalars(stmt)


def get_filtered_form_definitions_current(session, filter):
    stmt = select(FormDefinitionCurrent).filter_by(**filter)
    return session.scalars(stmt)


def get_form(trans, form_id):
    """Get a FormDefinition from the database by id."""
    form = trans.sa_session.query(FormDefinitionCurrent).get(trans.security.decode_id(form_id))
    if not form:
        return trans.show_error_message(f"Form not found for id ({str(form_id)})")
    return form


class FormManager(base.ModelManager[FormDefinitionCurrent]):
    """
    Business logic for forms.
    """

    def get(self, trans: ProvidesUserContext, form_id: int) -> FormDefinitionCurrent:
        """
        Method loads the form from the DB based on the given form id.

        :param  form_id:      id of the form to load from the DB
        :type   form_id:      int

        :returns:   the loaded Form object
        :rtype:     galaxy.model.FormDefinitionCurrent

        :raises: InconsistentDatabase, RequestParameterInvalidException, InternalServerError
        """
        try:
            stmt = select(FormDefinitionCurrent).where(FormDefinitionCurrent.id == form_id)
            form = self.session().execute(stmt).scalar_one()
        except MultipleResultsFound:
            raise InconsistentDatabase("Multiple forms found with the same id.")
        except NoResultFound:
            raise RequestParameterInvalidException("No accessible form found with the id provided.")
        except Exception as e:
            raise InternalServerError(f"Error loading from the database.{unicodify(e)}")
        return form

    def delete(self, trans: ProvidesUserContext, form: FormDefinitionCurrent) -> FormDefinitionCurrent:
        form.deleted = True
        trans.sa_session.add(form)
        trans.sa_session.commit()
        return form

    def undelete(self, trans: ProvidesUserContext, form: FormDefinitionCurrent) -> FormDefinitionCurrent:
        form.deleted = False
        trans.sa_session.add(form)
        trans.sa_session.commit()
        return form

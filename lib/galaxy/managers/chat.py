from typing import Union

from sqlalchemy import (
    and_,
    select,
)
from sqlalchemy.exc import (
    MultipleResultsFound,
    NoResultFound,
)

from galaxy.exceptions import (
    InconsistentDatabase,
    InternalServerError,
    RequestParameterInvalidException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import ChatExchange
from galaxy.util import unicodify


class ChatManager:
    """
    Business logic for chat exchanges.
    """

    def create(self, trans: ProvidesUserContext, job_id: int, message: str) -> ChatExchange:
        """
        Create a new chat exchange in the DB.  Currently these are *only* job-based chat exchanges, will need to generalize down the road.
        :param  job_id:      id of the job to associate the response with
        :type   job_id:      int
        :param  response:    the response to save in the DB
        :type   response:    str
        :returns:   the created ChatExchange object
        :rtype:     galaxy.model.ChatExchange
        :raises: InternalServerError
        """
        chat_exchange = ChatExchange(user=trans.user, job_id=job_id, message=message)
        trans.sa_session.add(chat_exchange)
        trans.sa_session.commit()
        return chat_exchange

    def get(self, trans: ProvidesUserContext, job_id: int) -> Union[ChatExchange, None]:
        """
        Returns the chat response from the DB based on the given job id.
        :param  job_id:      id of the job to load a response for from the DB
        :type   job_id:      int
        :returns:   the loaded ChatExchange object
        :rtype:     galaxy.model.ChatExchange
        :raises: InconsistentDatabase, InternalServerError
        """
        try:
            stmt = select(ChatExchange).where(
                and_(ChatExchange.job_id == job_id, ChatExchange.user_id == trans.user.id)
            )
            chat_response = trans.sa_session.execute(stmt).scalar_one()
        except MultipleResultsFound:
            # TODO: Unsure about this, isn't this more applicable when we're getting the response for response.id instead of response.
            raise InconsistentDatabase("Multiple chat responses found with the same job id.")
        except NoResultFound:
            # TODO: Would there be cases where we raise an exception here? Or, is there a better way to return None?
            # raise RequestParameterInvalidException("No accessible response found with the id provided.")
            return None
        except Exception as e:
            raise InternalServerError(f"Error loading from the database.{unicodify(e)}")
        return chat_response

    def set_feedback_for_job(self, trans: ProvidesUserContext, job_id: int, feedback: int) -> ChatExchange:
        """
        Set the feedback for a chat response.
        :param  message_id:      id of the job to associate the feedback with
        :type   message_id:      int
        :param  feedback:    the feedback to save in the DB (0 or 1)
        :type   feedback:    int
        :returns:   the updated ChatExchange object
        :rtype:     galaxy.model.ChatExchange
        :raises: RequestParameterInvalidException
        """

        # TODO: Set feedback for specific messages as we allow multiple messages per exchange, not this method targeting job.

        # Validate the feedback; it should be 0 or 1
        if feedback not in [0, 1]:
            raise RequestParameterInvalidException("Feedback should be 0 or 1.")

        chat_exchange = self.get(trans, job_id)

        if not chat_exchange:
            raise RequestParameterInvalidException("No accessible response found with the id provided.")

        # There is only one message in an exchange currently, so we can set the feedback on the first message
        chat_exchange.messages[0].feedback = feedback

        trans.sa_session.commit()

        return chat_exchange

import json
from typing import (
    Any,
    Optional,
    Union,
)

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from sqlalchemy import (
    and_,
    select,
)
from sqlalchemy.exc import (
    MultipleResultsFound,
    NoResultFound,
)

from galaxy import exceptions
from galaxy.exceptions import (
    InconsistentDatabase,
    InternalServerError,
    RequestParameterInvalidException,
)
from galaxy.managers import base
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import (
    ChatExchange,
    ChatExchangeMessage,
    Page,
)
from galaxy.util import unicodify


class ChatManager:
    """
    Business logic for chat exchanges.
    """

    def create(self, trans: ProvidesUserContext, job_id: Optional[int], message: str) -> ChatExchange:
        """
        Create a new chat exchange in the DB.  Currently these are *only* job-based chat exchanges, will need to generalize down the road.
        :param  job_id:      id of the job to associate the response with
        :type   job_id:      int
        :param  message:     the message to save in the DB
        :type   message:     str
        :returns:   the created ChatExchange object
        :rtype:     galaxy.model.ChatExchange
        :raises: InternalServerError
        """
        chat_exchange = ChatExchange(user=trans.user, job_id=job_id)

        # Create a message for this exchange
        chat_message = ChatExchangeMessage(message=message, feedback=None)
        chat_exchange.messages.append(chat_message)

        trans.sa_session.add(chat_exchange)
        trans.sa_session.add(chat_message)
        trans.sa_session.commit()
        return chat_exchange

    def get_accessible_page(self, trans: ProvidesUserContext, page_id: int) -> Page:
        """Return a Page the current user is allowed to read, or raise."""
        page = trans.sa_session.get(Page, page_id)
        if not page:
            raise exceptions.ObjectNotFound("Page not found")
        return base.security_check(trans, page, check_ownership=False, check_accessible=True)

    def create_page_chat(
        self,
        trans: ProvidesUserContext,
        page_id: int,
        query: str,
        response_data: Any,
        agent_type: str = "page_assistant",
    ) -> ChatExchange:
        """Create a chat exchange scoped to a page."""
        import json

        self.get_accessible_page(trans, page_id)
        chat_exchange = ChatExchange(user=trans.user, page_id=page_id)

        conversation_data: dict[str, Any]
        if isinstance(response_data, str):
            conversation_data = {"query": query, "response": response_data, "agent_type": agent_type}
        else:
            conversation_data = {
                "query": query,
                "response": (
                    response_data.get("response", "") if isinstance(response_data, dict) else str(response_data)
                ),
                "agent_type": agent_type,
                "agent_response": response_data.get("agent_response") if isinstance(response_data, dict) else None,
            }

        chat_message = ChatExchangeMessage(message=json.dumps(conversation_data), feedback=None)
        chat_exchange.messages.append(chat_message)

        trans.sa_session.add(chat_exchange)
        trans.sa_session.add(chat_message)
        trans.sa_session.commit()
        return chat_exchange

    def get_page_chat_history(self, trans: ProvidesUserContext, page_id: int, limit: int = 50) -> list[ChatExchange]:
        """Get chat exchanges scoped to a page, ordered most-recent first."""
        self.get_accessible_page(trans, page_id)
        try:
            stmt = (
                select(ChatExchange)
                .where(
                    and_(
                        ChatExchange.user_id == trans.user.id,
                        ChatExchange.page_id == page_id,
                    )
                )
                .order_by(ChatExchange.id.desc())
                .limit(limit)
            )
            return trans.sa_session.execute(stmt).scalars().all()
        except Exception as e:
            raise InternalServerError(f"Error loading page chat history: {unicodify(e)}")

    def create_general_chat(
        self, trans: ProvidesUserContext, query: str, response_data: Any, agent_type: str = "unknown"
    ) -> ChatExchange:
        """
        Create a general GalaxyAI exchange (not job-related) in the database.
        Stores both the user's query and the full agent response.

        :param query: The user's query
        :param response_data: The complete response data (can be string or dict with agent_response)
        :param agent_type: Type of agent that handled the query
        :returns: the created ChatExchange object
        """
        # Create exchange without job_id
        chat_exchange = ChatExchange(user=trans.user, job_id=None)

        # Store the full conversation as JSON in the message
        # This preserves both query and response with metadata
        import json

        # Handle both string responses and full agent response objects
        conversation_data: dict[str, Any]
        if isinstance(response_data, str):
            conversation_data = {
                "query": query,
                "response": response_data,
                "agent_type": agent_type,
            }
        else:
            # Preserve the full response structure including agent_response
            conversation_data = {
                "query": query,
                "response": (
                    response_data.get("response", "") if isinstance(response_data, dict) else str(response_data)
                ),
                "agent_type": agent_type,
                "agent_response": response_data.get("agent_response") if isinstance(response_data, dict) else None,
            }
        message_content = json.dumps(conversation_data)

        chat_message = ChatExchangeMessage(message=message_content, feedback=None)
        chat_exchange.messages.append(chat_message)

        trans.sa_session.add(chat_exchange)
        trans.sa_session.add(chat_message)
        trans.sa_session.commit()
        return chat_exchange

    def add_message(self, trans: ProvidesUserContext, exchange_id: int, message: str) -> ChatExchangeMessage:
        """
        Add a message to an existing chat exchange.
        :param  exchange_id: id of the exchange to add the message to
        :type   exchange_id: int
        :param  message:     the message to save in the DB
        :type   message:     str
        :returns:   the created ChatExchangeMessage object
        :rtype:     galaxy.model.ChatExchangeMessage
        :raises: RequestParameterInvalidException, InternalServerError
        """

        try:
            stmt = select(ChatExchange).where(
                and_(ChatExchange.id == exchange_id, ChatExchange.user_id == trans.user.id)
            )
            chat_exchange = trans.sa_session.execute(stmt).scalar_one()
        except MultipleResultsFound:
            raise InconsistentDatabase("Multiple chat exchanges found with the same ID.")
        except NoResultFound:
            raise RequestParameterInvalidException("No accessible chat exchange found with the ID provided.")
        except Exception as e:
            raise InternalServerError(f"Error loading from the database: {unicodify(e)}")

        chat_message = ChatExchangeMessage(message=message, feedback=None)
        chat_exchange.messages.append(chat_message)

        trans.sa_session.add(chat_message)
        trans.sa_session.commit()
        return chat_message

    def get(self, trans: ProvidesUserContext, job_id: int) -> Union[ChatExchange, None]:
        """
        Returns the chat exchange from the DB based on the given job id.
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
            chat_exchange = trans.sa_session.execute(stmt).scalar_one()
        except MultipleResultsFound:
            raise InconsistentDatabase("Multiple chat exchanges found with the same job id.")
        except NoResultFound:
            return None
        except Exception as e:
            raise InternalServerError(f"Error loading from the database: {unicodify(e)}")
        return chat_exchange

    def get_exchange_by_id(self, trans: ProvidesUserContext, exchange_id: int) -> Union[ChatExchange, None]:
        """
        Returns the chat exchange from the DB based on the exchange id.
        :param  exchange_id: id of the chat exchange to load from the DB
        :type   exchange_id: int
        :returns:   the loaded ChatExchange object
        :rtype:     galaxy.model.ChatExchange
        :raises: InconsistentDatabase, InternalServerError
        """
        try:
            stmt = select(ChatExchange).where(
                and_(ChatExchange.id == exchange_id, ChatExchange.user_id == trans.user.id)
            )
            chat_exchange = trans.sa_session.execute(stmt).scalar_one()
        except MultipleResultsFound:
            raise InconsistentDatabase("Multiple chat exchanges found with the same ID.")
        except NoResultFound:
            return None
        except Exception as e:
            raise InternalServerError(f"Error loading from the database: {unicodify(e)}")
        return chat_exchange

    def set_feedback_for_exchange(self, trans: ProvidesUserContext, exchange_id: int, feedback: int) -> ChatExchange:
        """
        Set the feedback for a chat exchange by exchange ID.
        :param  exchange_id: id of the chat exchange
        :type   exchange_id: int
        :param  feedback:    the feedback to save in the DB (0 or 1)
        :type   feedback:    int
        :returns:   the updated ChatExchange object
        :rtype:     galaxy.model.ChatExchange
        :raises: RequestParameterInvalidException
        """
        # Validate the feedback; it should be 0 or 1
        if feedback not in [0, 1]:
            raise RequestParameterInvalidException("Feedback should be 0 or 1.")

        chat_exchange = self.get_exchange_by_id(trans, exchange_id)

        if not chat_exchange:
            raise RequestParameterInvalidException("No accessible chat exchange found with the id provided.")

        # There is only one message in an exchange currently, so we can set the feedback on the first message
        chat_exchange.messages[0].feedback = feedback

        trans.sa_session.commit()

        return chat_exchange

    def set_feedback_for_job(self, trans: ProvidesUserContext, job_id: int, feedback: int) -> ChatExchange:
        """
        Set the feedback for a chat response.
        :param  job_id:      id of the job to associate the feedback with
        :type   job_id:      int
        :param  feedback:    the feedback to save in the DB (0 or 1)
        :type   feedback:    int
        :returns:   the updated ChatExchange object
        :rtype:     galaxy.model.ChatExchange
        :raises: RequestParameterInvalidException
        """
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

    @staticmethod
    def _messages_to_pydantic_ai(messages: list) -> list[ModelMessage]:
        """Reconstruct stored exchange messages as pydantic-ai history.

        Only the query/response text survives -- the stored ``agent_response`` (including
        ``agent_type``) is intentionally dropped here. Where the router needs that signal (to
        tell it is answering a clarification) ``get_routing_history`` reads it from storage.
        """
        pydantic_messages: list[ModelMessage] = []
        for msg in messages:
            try:
                data = json.loads(msg.message)
                if "query" in data:
                    pydantic_messages.append(ModelRequest(parts=[UserPromptPart(content=data["query"])]))
                if "response" in data:
                    pydantic_messages.append(ModelResponse(parts=[TextPart(content=data["response"])]))
            except (json.JSONDecodeError, KeyError):
                pydantic_messages.append(ModelResponse(parts=[TextPart(content=msg.message)]))
        return pydantic_messages

    @staticmethod
    def _message_is_clarification(message) -> bool:
        """Whether a stored message's response was a clarifying question (by ``agent_type``)."""
        try:
            data = json.loads(message.message)
        except (json.JSONDecodeError, TypeError):
            return False
        return (data.get("agent_response") or {}).get("agent_type") == "clarification"

    def get_routing_history(self, trans: ProvidesUserContext, exchange_id: int) -> tuple[list[ModelMessage], bool]:
        """The pydantic-ai conversation history plus whether the last turn was a clarification.

        Both are derived from a single exchange fetch. The router emits
        ``agent_type="clarification"`` when it needs more info; the next user message answers it.
        Routing withholds history, so routing that elliptical answer ("the second one") needs the
        flag to re-include the clarification turn.
        """
        exchange = self.get_exchange_by_id(trans, exchange_id)
        if not exchange or not exchange.messages:
            return [], False
        return self._messages_to_pydantic_ai(exchange.messages), self._message_is_clarification(exchange.messages[-1])

    def delete_exchange(self, trans: ProvidesUserContext, exchange_id: int) -> None:
        """Delete a single chat exchange and its messages."""
        exchange = self.get_exchange_by_id(trans, exchange_id)
        if not exchange:
            raise RequestParameterInvalidException("No accessible chat exchange found with the ID provided.")
        for message in exchange.messages:
            trans.sa_session.delete(message)
        trans.sa_session.delete(exchange)
        trans.sa_session.commit()

    def delete_exchanges(self, trans: ProvidesUserContext, exchange_ids: list[int]) -> int:
        """Delete multiple chat exchanges and their messages. Returns the count deleted."""
        count = 0
        for exchange_id in exchange_ids:
            exchange = self.get_exchange_by_id(trans, exchange_id)
            if exchange:
                for message in exchange.messages:
                    trans.sa_session.delete(message)
                trans.sa_session.delete(exchange)
                count += 1
        trans.sa_session.commit()
        return count

    def get_user_chat_history(
        self,
        trans: ProvidesUserContext,
        limit: int = 50,
        include_job_chats: bool = False,
        include_page_chats: bool = False,
    ) -> list[ChatExchange]:
        """
        Get all chat exchanges for a user.

        :param limit: Maximum number of exchanges to return
        :param include_job_chats: Whether to include job-related chats
        :param include_page_chats: Whether to include page-scoped chats
        :returns: List of ChatExchange objects
        """
        try:
            stmt = select(ChatExchange).where(ChatExchange.user_id == trans.user.id)

            if not include_job_chats:
                stmt = stmt.where(ChatExchange.job_id.is_(None))

            if not include_page_chats:
                stmt = stmt.where(ChatExchange.page_id.is_(None))

            stmt = stmt.order_by(ChatExchange.id.desc()).limit(limit)

            exchanges = trans.sa_session.execute(stmt).scalars().all()
            return exchanges
        except Exception as e:
            raise InternalServerError(f"Error loading chat history: {unicodify(e)}")

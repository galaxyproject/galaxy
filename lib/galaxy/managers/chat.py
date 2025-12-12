from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

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
from galaxy.model import (
    ChatExchange,
    ChatExchangeMessage,
)
from galaxy.util import unicodify

# Try to import pydantic-ai for enhanced chat functionality
try:
    from pydantic_ai import Agent
    from pydantic_ai.messages import (
        ModelMessage,
        ModelRequest,
        ModelResponse,
    )

    ModelRequest = ModelRequest

    HAS_PYDANTIC_AI = True
except ImportError:
    HAS_PYDANTIC_AI = False
    Agent = None
    ModelMessage = None
    ModelRequest = None
    ModelResponse = None


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

    def create_general_chat(
        self, trans: ProvidesUserContext, query: str, response_data: Any, agent_type: str = "unknown"
    ) -> ChatExchange:
        """
        Create a general ChatGXY exchange (not job-related) in the database.
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
        conversation_data: Dict[str, Any]
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

    def get_chat_history(
        self, trans: ProvidesUserContext, exchange_id: int, format_for_pydantic_ai: bool = False
    ) -> Union[List[Dict[str, Any]], List[ModelMessage]]:
        """
        Get the chat history for a specific exchange, optionally formatted for pydantic-ai.

        :param  exchange_id: id of the chat exchange
        :type   exchange_id: int
        :param  format_for_pydantic_ai: whether to format the history for pydantic-ai
        :type   format_for_pydantic_ai: bool
        :returns: list of chat messages
        :rtype: Union[List[Dict[str, Any]], List[ModelMessage]]
        """
        chat_exchange = self.get_exchange_by_id(trans, exchange_id)

        if not chat_exchange:
            return []

        messages = []
        import json

        if not format_for_pydantic_ai or not HAS_PYDANTIC_AI:
            # Format as simple role/content dictionaries
            for msg in chat_exchange.messages:
                try:
                    # Parse the JSON to get query and response
                    data = json.loads(msg.message)
                    # Add user message
                    if "query" in data:
                        messages.append({"role": "user", "content": data["query"]})
                    # Add assistant message
                    if "response" in data:
                        messages.append({"role": "assistant", "content": data["response"]})
                except (json.JSONDecodeError, KeyError):
                    # Fallback for non-JSON messages
                    messages.append({"role": "assistant", "content": msg.message})
            return messages
        else:
            # Format for pydantic-ai
            for msg in chat_exchange.messages:
                try:
                    data = json.loads(msg.message)
                    if "query" in data:
                        messages.append(ModelRequest(content=data["query"]))
                    if "response" in data:
                        messages.append(ModelResponse(content=data["response"]))
                except (json.JSONDecodeError, KeyError):
                    messages.append(ModelResponse(content=msg.message))
            return messages

    def get_user_chat_history(
        self, trans: ProvidesUserContext, limit: int = 50, include_job_chats: bool = False
    ) -> List[ChatExchange]:
        """
        Get all chat exchanges for a user.

        :param limit: Maximum number of exchanges to return
        :param include_job_chats: Whether to include job-related chats
        :returns: List of ChatExchange objects
        """
        try:
            stmt = select(ChatExchange).where(ChatExchange.user_id == trans.user.id)

            # Optionally filter out job-related chats
            if not include_job_chats:
                stmt = stmt.where(ChatExchange.job_id.is_(None))

            # Order by most recent first and apply limit
            stmt = stmt.order_by(ChatExchange.id.desc()).limit(limit)

            exchanges = trans.sa_session.execute(stmt).scalars().all()
            return exchanges
        except Exception as e:
            raise InternalServerError(f"Error loading chat history: {unicodify(e)}")

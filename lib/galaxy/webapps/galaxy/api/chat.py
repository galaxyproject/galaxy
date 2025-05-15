"""
API Controller providing Chat functionality
"""

import logging
from typing import (
    Optional,
    Union,
)

from fastapi import Path
from typing_extensions import Annotated

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ConfigurationError
from galaxy.managers.chat import ChatManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.jobs import JobManager
from galaxy.model import User
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    ChatPayload,
    ChatResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    DependsOnUser,
    Router,
)

try:
    import openai
except ImportError:
    openai = None

log = logging.getLogger(__name__)

router = Router(tags=["chat"])

DEFAULT_PROMPT = """
Please only say that something went wrong when configuing the ai prompt in your response.
"""

JobIdPathParam = Optional[
    Annotated[
        DecodedDatabaseIdField,
        Path(title="Job ID", description="The Job ID the chat exchange is linked to."),
    ]
]


@router.cbv
class ChatAPI:
    config: GalaxyAppConfiguration = depends(GalaxyAppConfiguration)
    chat_manager: ChatManager = depends(ChatManager)
    job_manager: JobManager = depends(JobManager)

    @router.post("/api/chat")
    def query(
        self,
        job_id: JobIdPathParam,
        payload: ChatPayload,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> ChatResponse:
        """We're off to ask the wizard and return a JSON response"""
        # Initialize response structure
        result = {"response": "", "error_code": 0, "error_message": ""}

        # Currently job-based chat exchanges are the only ones supported,
        # and will only have the one message.
        job = self.job_manager.get_accessible_job(trans, job_id)
        if job:
            # If there's an existing response for this job, just return that one for now.
            # TODO: Support regenerating the response as a new message, and
            # asking follow-up questions.
            existing_response = self.chat_manager.get(trans, job.id)
            if existing_response and existing_response.messages[0]:
                return ChatResponse(
                    response=existing_response.messages[0].message,
                    error_code=0,
                    error_message="",
                )

        self._ensure_openai_configured()

        messages = self._build_messages(payload, trans)

        try:
            # We never want this to just blow up and return *nothing*, so catch common errors and provide friendly responses.
            response = self._call_openai(messages)
            answer = response.choices[0].message.content
            result["response"] = answer
            if job:
                self.chat_manager.create(trans, job.id, answer)
        except openai.RateLimitError:
            result["response"] = (
                "Our AI assistant is experiencing high demand right now. Please try again in a few minutes, or contact an administrator if this persists."
            )
            result["error_code"] = 429
            result["error_message"] = "Rate limit exceeded"
        except Exception:
            result["error_code"] = 500
            result["error_message"] = (
                "Something unexpected happened. An error has been logged and administrators will look into it. Please try again later."
            )
        return ChatResponse(**result)

    @router.put("/api/chat/{job_id}/feedback")
    def feedback(
        self,
        job_id: JobIdPathParam,
        feedback: int,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> Union[int, None]:
        """Provide feedback on the chatbot response."""
        job = self.job_manager.get_accessible_job(trans, job_id)
        chat_response = self.chat_manager.set_feedback_for_job(trans, job.id, feedback)
        return chat_response.messages[0].feedback

    def _ensure_openai_configured(self):
        """Ensure OpenAI is available and configured with an API key."""
        if openai is None:
            raise ConfigurationError("OpenAI is not installed. Please install openai to use this feature.")
        if self.config.ai_api_key is None:
            raise ConfigurationError("OpenAI is not configured for this instance.")
        openai.api_key = self.config.ai_api_key
        if self.config.ai_api_base_url is not None:
            openai.base_url = self.config.ai_api_base_url

    def _get_system_prompt(self) -> str:
        """Get the system prompt for OpenAI."""
        return self.config.chat_prompts.get("tool_error", DEFAULT_PROMPT)

    def _build_messages(self, payload: ChatPayload, trans: ProvidesUserContext) -> list:
        """Build the message array to send to OpenAI."""
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": payload.query},
        ]
        return messages

    def _call_openai(self, messages: list):
        """Send a chat request to OpenAI and handle exceptions."""
        try:
            return openai.chat.completions.create(
                model=self.config.ai_model,
                messages=messages,
            )
        except openai.APIConnectionError:
            log.exception("OpenAI API Connection Error")
            raise ConfigurationError("An error occurred while connecting to OpenAI.")
        except openai.RateLimitError as e:
            # Wizard quota likely exceeded
            log.exception(f"A 429 status code was received; OpenAI rate limit exceeded.: ${e}")
            raise
        except Exception:
            # For anything else, it's likely a configuration issue and admins should be notified.
            raise ConfigurationError("An error occurred while communicating with OpenAI.")

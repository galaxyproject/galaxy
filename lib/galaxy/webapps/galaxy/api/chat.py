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
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import ChatPayload
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
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
    ) -> str:
        """We're off to ask the wizard"""
        # Currently job-based chat exchanges are the only ones supported,
        # and will only have the one message.
        job = self.job_manager.get_accessible_job(trans, job_id)
        if job:
            # If there's an existing response for this job, just return that one for now.
            # TODO: Support regenerating the response as a new message, and
            # asking follow-up questions.
            existing_response = self.chat_manager.get(trans, job.id)
            if existing_response and existing_response.messages[0]:
                return existing_response.messages[0].message

        self._ensure_openai_configured()

        messages = self._build_messages(payload, trans)
        response = self._call_openai(messages)
        answer = response.choices[0].message.content

        if job:
            self.chat_manager.create(trans, job.id, answer)

        return answer

    @router.put("/api/chat/{job_id}/feedback")
    def feedback(
        self,
        job_id: JobIdPathParam,
        feedback: int,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> Union[int, None]:
        """Provide feedback on the chatbot response."""
        job = self.job_manager.get_accessible_job(trans, job_id)
        chat_response = self.chat_manager.set_feedback_for_job(trans, job.id, feedback)
        return chat_response.messages[0].feedback

    def _ensure_openai_configured(self):
        """Ensure OpenAI is available and configured with an API key."""
        if openai is None:
            raise ConfigurationError("OpenAI is not installed. Please install openai to use this feature.")
        if self.config.openai_api_key is None:
            raise ConfigurationError("OpenAI is not configured for this instance.")
        openai.api_key = self.config.openai_api_key

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
                model=self.config.openai_model,
                messages=messages,
            )
        except Exception as e:
            log.error(f"Error calling OpenAI: {e}")
            raise ConfigurationError("An error occurred while communicating with OpenAI.")

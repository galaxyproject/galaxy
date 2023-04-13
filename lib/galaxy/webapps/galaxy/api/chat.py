"""
API Controller providing Chat functionality
"""
import logging

try:
    import openai
except ImportError:
    openai = None

from galaxy.config import GalaxyAppConfiguration
from galaxy.managers.context import ProvidesUserContext
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
)
from galaxy.exceptions import ConfigurationError
from galaxy.schema.schema import ChatPayload
from . import (
    depends,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["chat"])

PROMPT = """
You are a highly intelligent question answering agent, expert on the Galaxy analysis platform and in the fields of computer science, bioinformatics, and genomics.
You will try to answer questions about Galaxy, and if you don't know the answer, you will ask the user to rephrase the question.
"""


@router.cbv
class ChatAPI:
    config: GalaxyAppConfiguration = depends(GalaxyAppConfiguration)

    @router.post("/api/chat")
    def query(self, query: ChatPayload, trans: ProvidesUserContext = DependsOnTrans) -> str:
        """We're off to ask the wizard"""

        if openai is None or self.config.openai_api_key is None:
            raise ConfigurationError("OpenAI is not configured for this instance.")
        else:
            openai.api_key = self.config.openai_api_key

        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": query.query},
        ]

        if query.context == "username":
            user = trans.user
            if user is not None:
                log.debug(f"CHATGPTuser: {user.username}")
                msg = f"You will address the user as {user.username}"
            else:
                msg = f"You will address the user as Anonymous User"
            messages.append({"role": "system", "content": msg})
        elif query.context == "tool_error":
            msg = "The user will provide you a Galaxy tool error, and you will try to debug and explain what happened"
            messages.append({"role": "system", "content": msg})
        
        log.debug(f"CHATGPTmessages: {messages}")

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0,
        )

        answer = response["choices"][0]["message"]["content"]
        return answer

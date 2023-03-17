"""
API Controller providing Chat functionality
"""
import logging

import openai

from galaxy.config import GalaxyAppConfiguration
from galaxy.schema.schema import ChatPayload
from . import (
    depends,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["chat"])

prompt = """
I am a highly intelligent question answering agent, expert on Galaxy and in the fields of computer science, bioinformatics, and genomics.
If you ask me a question that I confidently know the answer to, I will give you the answer.
If you ask me a question that is nonsense, trickery, or has no clear answer, I will respond with "Unknown".

An example question is here:

Q: What is the Galaxy Project?
A: The Galaxy Project is an open, web-based platform for accessible, reproducible, and transparent computational biomedical research.

Q: ${query}
"""


@router.cbv
class ChatAPI:
    config: GalaxyAppConfiguration = depends(GalaxyAppConfiguration)

    @router.post("/api/chat")
    def query(self, query: ChatPayload) -> str:
        """We're off to ask the wizard"""

        if self.config.openai_api_key is None:
            return "OpenAI is not configured for this instance."
        else:
            openai.api_key = self.config.openai_api_key

        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt.format(query=query.query),
            temperature=0,
            max_tokens=400,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=["\n"],
        )
        answer = response.choices[0].text.strip()
        return answer

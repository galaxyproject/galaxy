"""
Plugins resource control over the API.
"""

import json
import logging
from typing import (
    Any,
    cast,
    Literal,
    Optional,
)

from fastapi import (
    Body,
    Path,
    Request,
)
from fastapi.responses import (
    JSONResponse,
    StreamingResponse,
)
from openai import AsyncOpenAI
from openai._streaming import AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)
from pydantic import BaseModel

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import (
    MessageException,
    ObjectNotFound,
)
from galaxy.managers import (
    hdas,
    histories,
)
from galaxy.model import User
from galaxy.structured_app import StructuredApp
from galaxy.util import asbool
from galaxy.web import expose_api_anonymous_and_sessionless
from galaxy.webapps.galaxy.api import (
    BaseGalaxyAPIController,
    depends,
    DependsOnApp,
    DependsOnUser,
    Router,
)
from galaxy.webapps.galaxy.fast_app import limiter

log = logging.getLogger(__name__)

router = Router(tags=["jobs"])

GALAXY_PROMPT = """
You are a Galaxy agent.
You assist users with scientific data analysis and research workflows.
Respond only to scientific, computational, or data analysis related questions.
"""

# Set constants
MAX_MESSAGES = 1024
MAX_TOOLS = 128
MAX_TOOL_BYTES = 16384
TEMPERATURE = 0.3
TIMEOUT = 120.0
TOKENS_DEFAULT = 1024
TOKENS_MAX = 8192
TOP_P = 0.9


class ChatMessage(BaseModel):
    role: Literal["assistant", "system", "tool", "user"]
    content: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None
    model_config = dict(extra="allow")


class ChatToolFunction(BaseModel):
    name: str
    model_config = dict(extra="allow")


class ChatTool(BaseModel):
    type: Literal["function"]
    function: ChatToolFunction
    model_config = dict(extra="allow")


class ChatCompletionRequest(BaseModel):
    messages: list[ChatMessage]
    tools: Optional[list[ChatTool]] = None
    stream: Optional[bool] = False
    max_tokens: Optional[int] = None
    model_config = dict(extra="allow")


@router.cbv
class FastAPIAI:
    app: StructuredApp = DependsOnApp
    config: GalaxyAppConfiguration = depends(GalaxyAppConfiguration)

    @router.post("/api/plugins/{plugin_name}/chat/completions", unstable=True)
    @limiter.limit("30/minute")
    async def plugins_chat_adapter(
        self,
        request: Request,
        payload: ChatCompletionRequest = Body(...),
        user: User = DependsOnUser,
        plugin_name: str = Path(
            ...,
            title="Plugin Name",
            description="Visualization plugin name used to resolve the AI prompt.",
            examples=["jupyterlite"],
        ),
    ):
        registry = self.app.visualizations_registry
        if registry:
            try:
                plugin = registry.get_plugin(plugin_name)
            except ObjectNotFound:
                return self.create_error(f"Plugin does not exist: {plugin_name}.")
            plugin_specs = plugin and plugin.config.get("specs")
            plugin_ai_prompt = plugin_specs and plugin_specs.get("ai_prompt")
            if plugin_ai_prompt:
                return await self._open_ai_adapter(payload, plugin_ai_prompt)
            else:
                return self.create_error("Selected plugin has no AI prompt.")
        else:
            return self.create_error("Visualization registry is not available.")

    async def _open_ai_adapter(
        self,
        payload: ChatCompletionRequest,
        prompt: str,
    ):
        """Galaxy managed chat completion adapter with prompt injection"""

        # Collect configuration
        ai_api_key = self.config.ai_api_key
        ai_api_base_url = self.config.ai_api_base_url
        ai_model = self.config.ai_model
        if ai_api_key is None:
            return self.create_error("AI service not configured: API key is required.")
        if ai_model is None:
            return self.create_error("AI service not configured: Model is required.")

        # Limit max tokens
        max_tokens = min(payload.max_tokens or TOKENS_DEFAULT, TOKENS_MAX)

        # Validate messages
        messages: list[ChatCompletionMessageParam] = cast(
            list[ChatCompletionMessageParam],
            [
                dict(role="system", content=GALAXY_PROMPT),
                dict(role="system", content=prompt),
            ],
        )
        original_messages = payload.messages
        for msg in original_messages:
            role = msg.role
            content = msg.content
            tool_calls = msg.tool_calls
            if role == "assistant":
                msg_dict: dict[str, Any] = dict(role="assistant")
                if content is not None:
                    msg_dict["content"] = content
                if isinstance(tool_calls, list):
                    msg_dict["tool_calls"] = tool_calls
                if len(msg_dict) > 1:
                    messages.append(cast(ChatCompletionMessageParam, msg_dict))
            elif role in ("user", "tool") and isinstance(content, str):
                messages.append(cast(ChatCompletionMessageParam, dict(role=role, content=content)))
            else:
                continue
            if len(messages) >= MAX_MESSAGES:
                return self.create_error("You have exceeded the number of maximum messages.")

        # Detect streaming flag
        stream = payload.stream is True

        # Limit number and size of tools
        tools: list[ChatCompletionToolParam] = []
        original_tools = payload.tools or []
        if len(original_tools) <= MAX_TOOLS:
            for tool in original_tools:
                tool_dict = tool.model_dump()
                size = len(json.dumps(tool_dict, separators=(",", ":")).encode("utf-8"))
                if size > MAX_TOOL_BYTES:
                    return self.create_error("Tool schema too large.")
                tools.append(cast(ChatCompletionToolParam, tool_dict))
        else:
            return self.create_error("Number of tools exceeded or invalid tools list.")

        # Build openai client with timeout
        client_kwargs = dict(api_key=ai_api_key, timeout=TIMEOUT)
        if ai_api_base_url:
            client_kwargs["base_url"] = ai_api_base_url
        try:
            client = AsyncOpenAI(**client_kwargs)
        except Exception as e:
            log.debug("Failed to initialize OpenAI client.", exc_info=e)
            return self.create_error("Failed to initialize OpenAI client.", 500)

        # Connect to ai provider
        log.info(f"Proxying to {ai_model}, tokens: {max_tokens}.")
        try:
            response = await client.chat.completions.create(
                max_tokens=max_tokens,
                messages=messages,
                model=ai_model,
                stream=stream,
                temperature=TEMPERATURE,
                tools=tools,
                top_p=TOP_P,
            )
        except Exception as e:
            log.debug("Failed to complete OpenAI request.", exc_info=e)
            status_code = getattr(e, "status_code", 500)
            if hasattr(e, "body") and isinstance(e.body, dict):
                return JSONResponse(content=dict(error=e.body), status_code=status_code)
            return self.create_error("Failed to complete OpenAI request.", status_code)

        # Parse response
        if stream:
            stream_response: AsyncStream[ChatCompletionChunk] = cast(AsyncStream[ChatCompletionChunk], response)

            async def generate():
                try:
                    async for chunk in stream_response:
                        yield f"data: {json.dumps(chunk.model_dump())}\n\n"
                    yield "data: [DONE]\n\n"
                finally:
                    await client.close()

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            completion_response: ChatCompletion = cast(ChatCompletion, response)
            return JSONResponse(content=completion_response.model_dump())

    def create_error(self, message: str, status_code=400):
        """Error handling helper."""
        log.debug(message)
        return JSONResponse(content=dict(error=dict(message=message)), status_code=status_code)


class PluginsController(BaseGalaxyAPIController):
    """
    RESTful controller for interactions with plugins.
    """

    hda_manager: hdas.HDAManager = depends(hdas.HDAManager)
    history_manager: histories.HistoryManager = depends(histories.HistoryManager)

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwargs):
        """
        GET /api/plugins:
        """
        registry = self._get_registry()
        embeddable = asbool(kwargs.get("embeddable"))
        target_object = None
        if (dataset_id := kwargs.get("dataset_id")) is not None:
            target_object = self.hda_manager.get_accessible(self.decode_id(dataset_id), trans.user)
        return registry.get_visualizations(trans, target_object=target_object, embeddable=embeddable)

    @expose_api_anonymous_and_sessionless
    def show(self, trans, id, **kwargs):
        """
        GET /api/plugins/{id}:
        """
        registry = self._get_registry()
        if (history_id := kwargs.get("history_id")) is not None:
            history = self.history_manager.get_owned(
                trans.security.decode_id(history_id), trans.user, current_history=trans.history
            )
            result = {"hdas": []}
            for hda in history.contents_iter(types=["dataset"], deleted=False, visible=True):
                if registry.get_visualization(trans, id, hda):
                    result["hdas"].append({"id": trans.security.encode_id(hda.id), "hid": hda.hid, "name": hda.name})
            result["hdas"].sort(key=lambda h: h["hid"], reverse=True)
        else:
            result = registry.get_plugin(id).to_dict()
        return result

    def _get_registry(self):
        if not self.app.visualizations_registry:
            raise MessageException("The visualization registry has not been configured.")
        return self.app.visualizations_registry

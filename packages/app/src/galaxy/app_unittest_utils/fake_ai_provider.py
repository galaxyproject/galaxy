"""An OpenAI-compatible chat completions endpoint served from the test process.

Point Galaxy's AI base URLs at it and Galaxy uses the real OpenAI client against a
scripted reply, so tests can assert on the request that actually reached the provider.
"""

import json
from typing import Any

from galaxy.util.unittest_utils.test_http_server import (
    RecordedRequest,
    RecordingHttpServer,
)


def completion_chunk(content: str, **chunk: Any) -> dict[str, Any]:
    return {
        "id": "chunk",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "fake_model",
        "choices": [{"index": 0, "delta": {"content": content}}],
        **chunk,
    }


class FakeAIProvider:
    def __init__(self) -> None:
        self.server = RecordingHttpServer()

    def start(self) -> None:
        self.server.start()

    def stop(self) -> None:
        self.server.stop()

    def clear(self) -> None:
        self.server.clear()

    def base_url(self, prefix: str = "/v1") -> str:
        return self.server.url_for(prefix)

    def respond_completion(self, prefix: str = "/v1", **response: Any) -> None:
        completion = {"id": "test", "object": "chat.completion", "created": 0, "model": "fake_model", "choices": []}
        self._respond_json(prefix, {**completion, **response})

    def respond_message(
        self, content: str | None = None, tool_calls: list[dict[str, Any]] | None = None, prefix: str = "/v1"
    ) -> None:
        message: dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        finish_reason = "tool_calls" if tool_calls else "stop"
        self.respond_completion(prefix, choices=[{"index": 0, "message": message, "finish_reason": finish_reason}])

    def respond_tool_call(self, name: str, arguments: dict[str, Any], prefix: str = "/v1") -> None:
        tool_call = {"id": "call_1", "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}
        self.respond_message(tool_calls=[tool_call], prefix=prefix)

    def respond_stream(self, *chunks: dict[str, Any], prefix: str = "/v1") -> None:
        data = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"
        self.server.add_route(self._path(prefix), body=data, content_type="text/event-stream", request_method="POST")

    def respond_error(self, status: int, error: dict[str, Any], prefix: str = "/v1") -> None:
        self._respond_json(prefix, {"error": error}, status=status)

    @property
    def requests(self) -> list[RecordedRequest]:
        return self.server.requests

    def last_request(self) -> RecordedRequest:
        assert self.requests, "no request reached the provider"
        return self.requests[-1]

    def last_body(self) -> Any:
        return self.last_request().json()

    def _respond_json(self, prefix: str, data: dict[str, Any], status: int = 200) -> None:
        self.server.add_json_route(self._path(prefix), data, status=status, request_method="POST")

    def _path(self, prefix: str) -> str:
        return f"{prefix}/chat/completions"

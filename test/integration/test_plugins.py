import os
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest

from galaxy_test.driver.integration_util import IntegrationTestCase

openai = pytest.importorskip("openai")

TEST_VISUALIZATION_PLUGINS_DIR = os.path.join(os.path.dirname(__file__), "test_visualization_plugins")


class TestAiApi(IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        config["ai_api_key"] = "ai_api_key"
        config["ai_api_base_url"] = "ai_api_base_url"
        config["ai_model"] = "ai_model"
        config["visualization_plugins_directory"] = TEST_VISUALIZATION_PLUGINS_DIR

    def _create_payload(self, extra=None):
        payload = {
            "messages": [{"role": "user", "content": "hi"}],
            "tools": [],
        }
        if extra:
            payload.update(extra)
        return payload

    def _post_payload(self, payload=None, anon=False):
        return self._post("plugins/jupyterlite/chat/completions", payload, json=True, anon=anon)

    @patch("galaxy.webapps.galaxy.api.plugins.AsyncOpenAI")
    def test_non_streaming_success(self, mock_client):
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {"id": "test", "choices": []}
        mock_instance = MagicMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance
        payload = self._create_payload()
        response = self._post_payload(payload, anon=False)
        self._assert_status_code_is(response, 200)
        assert response.json()["id"] == "test"

    @patch("galaxy.webapps.galaxy.api.plugins.AsyncOpenAI")
    def test_streaming_success(self, mock_client):
        async def stream_gen():
            chunk1 = MagicMock()
            chunk1.model_dump.return_value = {"choices": [{"delta": {"content": "hello"}}]}
            chunk2 = MagicMock()
            chunk2.model_dump.return_value = {"choices": [{"delta": {"content": "world"}}]}
            yield chunk1
            yield chunk2

        mock_instance = MagicMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=stream_gen())
        mock_instance.close = AsyncMock()
        mock_client.return_value = mock_instance
        payload = self._create_payload({"stream": True})
        response = self._post_payload(payload, anon=False)
        self._assert_status_code_is(response, 200)
        body = response.text
        assert body.count("data:") == 3
        assert "hello" in body
        assert "world" in body
        assert body.rstrip().endswith("data: [DONE]")
        assert mock_instance.chat.completions.create.called
        assert mock_instance.close.called

    def test_tools_exceed_max(self):
        payload = self._create_payload(
            {"tools": [{"type": "function", "function": {"name": "f", "parameters": {}}}] * 129}
        )
        response = self._post_payload(payload)
        assert "Number of tools exceeded" in response.json()["error"]["message"]

    def test_tool_schema_too_large(self):
        big_params = {"x": "a" * 20000}
        payload = self._create_payload(
            {"tools": [{"type": "function", "function": {"name": "f", "parameters": big_params}}]}
        )
        response = self._post_payload(payload)
        assert "Tool schema too large" in response.json()["error"]["message"]

    def test_exceed_max_messages(self):
        msgs = {"messages": [{"role": "user", "content": "x"}] * (1024 + 1)}
        payload = self._create_payload(msgs)
        response = self._post_payload(payload)
        assert "You have exceeded the number of maximum messages" in response.json()["error"]["message"]

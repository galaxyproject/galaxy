from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest

from galaxy_test.driver.integration_util import IntegrationTestCase

openai = pytest.importorskip("openai")


class TestAiApi(IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        config["ai_api_key"] = "ai_api_key"
        config["ai_api_base_url"] = "ai_api_base_url"
        config["ai_model"] = "ai_model"

    def _create_payload(self, extra=None):
        payload = {
            "messages": [{"role": "user", "content": "hi"}],
            "tools": [],
        }
        if extra:
            payload.update(extra)
        return payload

    def _post_payload(self, payload=None, anon=False):
        return self._post("ai/plugins/jupyterlite/chat/completions", payload, json=True, anon=anon)

    def _mock_plugin(self, mock_get_plugin):
        mock_plugin = MagicMock()
        mock_plugin.config = {"specs": {"ai_prompt": "test prompt"}}
        mock_get_plugin.return_value = mock_plugin

    @patch("galaxy.webapps.galaxy.api.ai.AsyncOpenAI")
    @patch("galaxy.visualization.plugins.registry.VisualizationsRegistry.get_plugin")
    def test_non_streaming_success(self, mock_get_plugin, mock_client):
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {"id": "test", "choices": []}
        mock_instance = MagicMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance
        self._mock_plugin(mock_get_plugin)
        payload = self._create_payload()
        response = self._post_payload(payload, anon=False)
        self._assert_status_code_is(response, 200)
        assert response.json()["id"] == "test"

    @patch("galaxy.webapps.galaxy.api.ai.AsyncOpenAI")
    @patch("galaxy.visualization.plugins.registry.VisualizationsRegistry.get_plugin")
    def test_streaming_success(self, mock_get_plugin, mock_client):
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
        self._mock_plugin(mock_get_plugin)
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

    @patch("galaxy.visualization.plugins.registry.VisualizationsRegistry.get_plugin")
    def test_tools_exceed_max(self, mock_get_plugin):
        self._mock_plugin(mock_get_plugin)
        payload = self._create_payload(
            {"tools": [{"type": "function", "function": {"name": "f", "parameters": {}}}] * 129}
        )
        response = self._post_payload(payload)
        assert "Number of tools exceeded" in response.json()["error"]["message"]

    @patch("galaxy.visualization.plugins.registry.VisualizationsRegistry.get_plugin")
    def test_tool_schema_too_large(self, mock_get_plugin):
        self._mock_plugin(mock_get_plugin)
        big_params = {"x": "a" * 20000}
        payload = self._create_payload(
            {"tools": [{"type": "function", "function": {"name": "f", "parameters": big_params}}]}
        )
        response = self._post_payload(payload)
        assert "Tool schema too large" in response.json()["error"]["message"]

    @patch("galaxy.visualization.plugins.registry.VisualizationsRegistry.get_plugin")
    def test_exceed_max_messages(self, mock_get_plugin):
        self._mock_plugin(mock_get_plugin)
        msgs = {"messages": [{"role": "user", "content": "x"}] * (1024 + 1)}
        payload = self._create_payload(msgs)
        response = self._post_payload(payload)
        assert "You have exceeded the number of maximum messages" in response.json()["error"]["message"]

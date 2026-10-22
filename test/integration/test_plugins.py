import os
from unittest.mock import patch

import pytest

from galaxy.app_unittest_utils.fake_ai_provider import completion_chunk
from galaxy_test.driver.integration_util import (
    IntegrationTestCase,
    UsesFakeAIProvider,
)

openai = pytest.importorskip("openai")

TEST_VISUALIZATION_PLUGINS_DIR = os.path.join(os.path.dirname(__file__), "test_visualization_plugins")


def _create_chat_payload(extra=None):
    payload = {
        "messages": [{"role": "user", "content": "hi"}],
        "tools": [],
    }
    if extra:
        payload.update(extra)
    return payload


class FakeAIProviderTestCase(UsesFakeAIProvider, IntegrationTestCase):
    def _post_payload(self, payload=None, anon=False):
        return self._post("plugins/jupyterlite/chat/completions", payload, json=True, anon=anon)


class TestVisualizationPluginsApi(FakeAIProviderTestCase):
    """Tests for the visualization plugins API endpoints."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        config["ai_api_key"] = "ai_api_key"
        config["ai_api_base_url"] = cls.fake_ai_provider.base_url()
        config["ai_model"] = "ai_model"
        config["visualization_plugins_directory"] = TEST_VISUALIZATION_PLUGINS_DIR

    def test_index(self):
        """Test that GET /api/plugins returns a list of plugins."""
        response = self._get("plugins")
        self._assert_status_code_is(response, 200)
        plugins = response.json()
        assert isinstance(plugins, list)

    def test_show_returns_all_fields(self):
        """Test that GET /api/plugins/{id} returns all expected fields including params, tags, tests, help, data_sources."""
        response = self._get("plugins/jupyterlite")
        self._assert_status_code_is(response, 200)
        plugin = response.json()

        # Verify required fields
        assert plugin["name"] == "jupyterlite"
        assert plugin["html"] == "JupyterLite Test"
        assert plugin["description"] == "Test fixture for visualization plugin integration tests"
        assert plugin["embeddable"] is False
        assert "entry_point" in plugin
        assert "href" in plugin

        # Verify params are returned correctly
        assert "params" in plugin
        params = plugin["params"]
        assert "dataset_id" in params
        assert params["dataset_id"]["required"] is True
        assert params["dataset_id"]["type"] == "str"

        # Verify data_sources are returned
        assert "data_sources" in plugin
        data_sources = plugin["data_sources"]
        assert len(data_sources) >= 1
        assert data_sources[0]["model_class"] == "HistoryDatasetAssociation"

        # Verify specs are returned
        assert "specs" in plugin
        assert plugin["specs"]["custom_setting"] == "test_value"

        # Verify tags are returned
        assert "tags" in plugin
        tags = plugin["tags"]
        assert "Test" in tags
        assert "Integration" in tags

        # Verify help is returned
        assert "help" in plugin
        assert "test help text" in plugin["help"]

        # Verify tests are returned
        assert "tests" in plugin
        assert len(plugin["tests"]) >= 1

    def test_non_streaming_success(self):
        self.fake_ai_provider.respond_completion()
        response = self._post_payload(_create_chat_payload())
        self._assert_status_code_is(response, 200)
        assert response.json()["id"] == "test"
        request = self.fake_ai_provider.last_request()
        assert request.headers["Authorization"] == "Bearer ai_api_key"
        assert self.fake_ai_provider.last_body()["stream"] is False

    def test_streaming_success(self):
        self.fake_ai_provider.respond_stream(completion_chunk("hello"), completion_chunk("world"))
        closed = []
        close = openai.AsyncOpenAI.close

        async def record_close(client):
            closed.append(client)
            await close(client)

        with patch.object(openai.AsyncOpenAI, "close", record_close):
            response = self._post_payload(_create_chat_payload({"stream": True}))
        self._assert_status_code_is(response, 200)
        body = response.text
        assert body.count("data:") == 3
        assert "hello" in body
        assert "world" in body
        assert body.rstrip().endswith("data: [DONE]")
        assert self.fake_ai_provider.last_body()["stream"] is True
        assert closed

    def test_stream_options_forwarded_when_streaming(self):
        stream_options = {"include_usage": True}
        for extra, expected in (
            ({"stream": True, "stream_options": stream_options}, stream_options),
            ({"stream": True}, None),
            ({"stream": False, "stream_options": stream_options}, None),
        ):
            self.fake_ai_provider.clear()
            if extra["stream"]:
                self.fake_ai_provider.respond_stream(completion_chunk("", choices=[], usage={"total_tokens": 3}))
            else:
                self.fake_ai_provider.respond_completion()
            response = self._post_payload(_create_chat_payload(extra))
            self._assert_status_code_is(response, 200)
            assert self.fake_ai_provider.last_body().get("stream_options") == expected

    def test_standard_options_forwarded(self):
        self.fake_ai_provider.respond_completion()
        options = {
            "parallel_tool_calls": False,
            "reasoning_effort": "low",
            "tool_choice": {"type": "function", "function": {"name": "get_version"}},
        }
        payload = _create_chat_payload(
            {"tools": [{"type": "function", "function": {"name": "get_version"}}], **options}
        )
        response = self._post_payload(payload)
        self._assert_status_code_is(response, 200)
        sent = self.fake_ai_provider.last_body()
        assert {key: sent[key] for key in options} == options
        response = self._post_payload(_create_chat_payload())
        self._assert_status_code_is(response, 200)
        sent = self.fake_ai_provider.last_body()
        assert not options.keys() & sent.keys()

    def test_tools_exceed_max(self):
        payload = _create_chat_payload(
            {"tools": [{"type": "function", "function": {"name": "f", "parameters": {}}}] * 129}
        )
        response = self._post_payload(payload)
        assert "Number of tools exceeded" in response.json()["error"]["message"]
        assert not self.fake_ai_provider.requests

    def test_tool_schema_too_large(self):
        big_params = {"x": "a" * 20000}
        payload = _create_chat_payload(
            {"tools": [{"type": "function", "function": {"name": "f", "parameters": big_params}}]}
        )
        response = self._post_payload(payload)
        assert "Tool schema too large" in response.json()["error"]["message"]
        assert not self.fake_ai_provider.requests

    def test_exceed_max_messages(self):
        msgs = {"messages": [{"role": "user", "content": "x"}] * (1024 + 1)}
        payload = _create_chat_payload(msgs)
        response = self._post_payload(payload)
        assert "You have exceeded the number of maximum messages" in response.json()["error"]["message"]
        assert not self.fake_ai_provider.requests

    def test_assistant_content_and_tool_calls_preserved(self):
        self.fake_ai_provider.respond_completion()
        payload = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "I will call a tool",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "choose_process",
                                "arguments": "{}",
                            },
                        }
                    ],
                }
            ],
            "tools": [],
        }
        response = self._post_payload(payload)
        self._assert_status_code_is(response, 200)
        forwarded_messages = self.fake_ai_provider.last_body()["messages"]
        assistant_msgs = [m for m in forwarded_messages if m["role"] == "assistant"]
        assert len(assistant_msgs) == 1
        assert assistant_msgs[0]["content"] == "I will call a tool"
        assert "tool_calls" in assistant_msgs[0]
        assert assistant_msgs[0]["tool_calls"][0]["function"]["name"] == "choose_process"
        assert assistant_msgs[0]["tool_calls"][0]["function"]["arguments"] == "{}"

    def test_messages_forwarded_as_sent(self):
        self.fake_ai_provider.respond_completion()
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "Which version?"}], "name": "analyst"},
            {
                "role": "assistant",
                "reasoning_content": "I should call get_version.",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_version", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "content": "26.1", "tool_call_id": "call_1", "x_vendor": {"tag": [1]}},
        ]
        payload = {"messages": messages, "tools": [{"type": "function", "function": {"name": "get_version"}}]}
        response = self._post_payload(payload)
        self._assert_status_code_is(response, 200)
        assert self.fake_ai_provider.last_body()["messages"][2:] == messages

    def test_client_system_messages_replaced(self):
        self.fake_ai_provider.respond_completion()
        payload = {
            "messages": [
                {"role": "system", "content": "client prompt", "x_vendor": 1},
                {"role": "user", "content": "hi"},
                {"role": "system", "content": "client update"},
                {"role": "user", "content": "again"},
            ]
        }
        response = self._post_payload(payload)
        self._assert_status_code_is(response, 200)
        forwarded_messages = self.fake_ai_provider.last_body()["messages"]
        assert [m["role"] for m in forwarded_messages[:2]] == ["system", "system"]
        assert forwarded_messages[2:] == [{"role": "user", "content": "hi"}, {"role": "user", "content": "again"}]

    def test_non_text_content_part_refused(self):
        payload = _create_chat_payload(
            {"messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "x"}}]}]}
        )
        response = self._post_payload(payload)
        self._assert_status_code_is(response, 400)
        assert not self.fake_ai_provider.requests

    def test_messages_without_content_dropped(self):
        self.fake_ai_provider.respond_completion()
        payload = {
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": None, "reasoning_content": "thinking only"},
                {"role": "tool", "tool_call_id": "call_1", "x_vendor": 1},
            ]
        }
        response = self._post_payload(payload)
        self._assert_status_code_is(response, 200)
        forwarded_messages = self.fake_ai_provider.last_body()["messages"]
        assert [m["role"] for m in forwarded_messages] == ["system", "system", "user"]

    def test_top_level_extensions_not_forwarded(self):
        self.fake_ai_provider.respond_completion()
        payload = _create_chat_payload(
            {"x_vendor": 1, "model": "client-model", "n": 4, "temperature": 1.5, "top_p": 0.1}
        )
        response = self._post_payload(payload)
        self._assert_status_code_is(response, 200)
        sent = self.fake_ai_provider.last_body()
        assert "x_vendor" not in sent
        assert "n" not in sent
        assert sent["model"] == "ai_model"
        assert (sent["temperature"], sent["top_p"]) == (0.3, 0.9)

    def test_inference_settings_without_config(self):
        self.fake_ai_provider.respond_completion()
        for client_max_tokens, max_tokens in ((None, 1024), (100000, 8192)):
            response = self._post_payload(_create_chat_payload({"max_tokens": client_max_tokens}))
            self._assert_status_code_is(response, 200)
            sent = self.fake_ai_provider.last_body()
            assert (sent["temperature"], sent["top_p"]) == (0.3, 0.9)
            assert sent["max_tokens"] == max_tokens
            assert float(self.fake_ai_provider.last_request().headers["x-stainless-read-timeout"]) == 120.0

    def test_empty_tools_omitted(self):
        self.fake_ai_provider.respond_completion()
        for payload in (_create_chat_payload(), {"messages": [{"role": "user", "content": "hi"}]}):
            response = self._post_payload(payload)
            self._assert_status_code_is(response, 200)
            assert "tools" not in self.fake_ai_provider.last_body()

    def test_tool_description_preserved(self):
        self.fake_ai_provider.respond_completion()
        payload = _create_chat_payload(
            {
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "choose_process",
                            "description": "Select a processing step",
                            "parameters": {"type": "object"},
                        },
                    }
                ]
            }
        )
        response = self._post_payload(payload)
        self._assert_status_code_is(response, 200)
        forwarded_tools = self.fake_ai_provider.last_body()["tools"]
        assert forwarded_tools[0]["function"]["description"] == "Select a processing step"

    def test_tool_with_none_parameters_normalized(self):
        self.fake_ai_provider.respond_completion()
        payload = _create_chat_payload(
            {
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "choose_process",
                            "description": "Select a processing step",
                            "parameters": None,
                        },
                    }
                ]
            }
        )
        response = self._post_payload(payload)
        self._assert_status_code_is(response, 200)
        forwarded_tools = self.fake_ai_provider.last_body()["tools"]
        assert forwarded_tools[0]["function"]["parameters"] == {
            "type": "object",
            "properties": {},
        }

    def test_tool_with_missing_parameters_normalized(self):
        self.fake_ai_provider.respond_completion()
        payload = _create_chat_payload(
            {
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "choose_process",
                            "description": "Select a processing step",
                        },
                    }
                ]
            }
        )
        response = self._post_payload(payload)
        self._assert_status_code_is(response, 200)
        forwarded_tools = self.fake_ai_provider.last_body()["tools"]
        assert forwarded_tools[0]["function"]["parameters"] == {
            "type": "object",
            "properties": {},
        }

    def test_provider_error_body_forwarded(self):
        # 4xx: the OpenAI client retries 5xx and 429 with backoff.
        error = {"message": "original error message", "type": "api_error", "param": None, "code": None}
        self.fake_ai_provider.respond_error(404, error)
        response = self._post_payload(_create_chat_payload())
        self._assert_status_code_is(response, 404)
        body = response.json()
        assert body["error"]["message"] == "original error message"
        assert body["error"]["type"] == "api_error"


class TestPluginsInferenceServicesConfig(FakeAIProviderTestCase):
    """Tests for inference_services config resolution in plugins."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        config["ai_api_key"] = "global_key"
        config["ai_api_base_url"] = cls.fake_ai_provider.base_url("/global/v1")
        config["ai_model"] = "global_model"
        config["visualization_plugins_directory"] = TEST_VISUALIZATION_PLUGINS_DIR
        config["inference_services"] = {
            "default": {
                "model": "default_model",
                "api_key": "default_key",
                "api_base_url": cls.fake_ai_provider.base_url("/default/v1"),
                "max_tokens": 512,
                "temperature": 0.5,
                "timeout": 30,
                "top_p": 0.6,
            },
            "jupyterlite": {
                "model": "jupyterlite_model",
                "api_key": "jupyterlite_key",
                "api_base_url": cls.fake_ai_provider.base_url("/jupyterlite/v1"),
                "max_tokens": 4096,
                "temperature": 0.7,
                "timeout": 60,
                "top_p": 0.8,
            },
        }

    def test_plugin_specific_config_used(self):
        """Plugin-specific inference_services config overrides default and global."""
        self.fake_ai_provider.respond_completion(prefix="/jupyterlite/v1")
        response = self._post_payload(payload=_create_chat_payload())
        self._assert_status_code_is(response, 200)
        request = self.fake_ai_provider.last_request()
        assert request.path == "/jupyterlite/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer jupyterlite_key"
        assert self.fake_ai_provider.last_body()["model"] == "jupyterlite_model"

    def test_plugin_specific_settings_used(self):
        """Plugin-specific inference settings override the default block and the built-in policy."""
        self.fake_ai_provider.respond_completion(prefix="/jupyterlite/v1")
        for client_max_tokens, max_tokens in ((None, 1024), (2048, 2048), (100000, 4096)):
            response = self._post_payload(payload=_create_chat_payload({"max_tokens": client_max_tokens}))
            self._assert_status_code_is(response, 200)
            sent = self.fake_ai_provider.last_body()
            assert (sent["temperature"], sent["top_p"]) == (0.7, 0.8)
            assert sent["max_tokens"] == max_tokens
            assert float(self.fake_ai_provider.last_request().headers["x-stainless-read-timeout"]) == 60.0


class TestPluginsInferenceServicesDefault(FakeAIProviderTestCase):
    """Tests that inference_services.default is used when no plugin-specific config exists."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        config["ai_api_key"] = "global_key"
        config["ai_api_base_url"] = cls.fake_ai_provider.base_url("/global/v1")
        config["ai_model"] = "global_model"
        config["visualization_plugins_directory"] = TEST_VISUALIZATION_PLUGINS_DIR
        config["inference_services"] = {
            "default": {
                "model": "default_model",
                "api_key": "default_key",
                "api_base_url": cls.fake_ai_provider.base_url("/default/v1"),
                "max_tokens": 512,
                "temperature": 0.5,
                "timeout": 30,
                "top_p": 0.6,
            },
        }

    def test_default_config_fallback(self):
        """inference_services.default is used when no plugin-specific entry exists."""
        self.fake_ai_provider.respond_completion(prefix="/default/v1")
        response = self._post_payload(payload=_create_chat_payload())
        self._assert_status_code_is(response, 200)
        request = self.fake_ai_provider.last_request()
        assert request.path == "/default/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer default_key"
        assert self.fake_ai_provider.last_body()["model"] == "default_model"

    def test_default_settings_inherited(self):
        """Inference settings in inference_services.default apply when the plugin sets none."""
        self.fake_ai_provider.respond_completion(prefix="/default/v1")
        for client_max_tokens, max_tokens in ((None, 512), (100000, 512)):
            response = self._post_payload(payload=_create_chat_payload({"max_tokens": client_max_tokens}))
            self._assert_status_code_is(response, 200)
            sent = self.fake_ai_provider.last_body()
            assert (sent["temperature"], sent["top_p"]) == (0.5, 0.6)
            assert sent["max_tokens"] == max_tokens
            assert float(self.fake_ai_provider.last_request().headers["x-stainless-read-timeout"]) == 30.0

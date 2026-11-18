import json
import os
import shutil
import time

from galaxy.util import galaxy_directory
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

FIXTURE = "chat_fixture"
FIXTURE_DIRECTORY = os.path.join(os.path.dirname(__file__), "galaxy_ai_chat", FIXTURE)
STAGED_FIXTURE = os.path.join(galaxy_directory(), "static", "plugins", "visualizations", FIXTURE)
CHAT = {
    "agent_type": FIXTURE,
    "messages": [{"query": "Which aligner?", "response": "HISAT2."}],
    "document": {"turns": 1},
}


def _create_chat(test):
    raw = test.execute_script(
        "const request = new XMLHttpRequest();"
        "request.open('POST', '/api/chat/exchanges', false);"
        "request.setRequestHeader('Content-Type', 'application/json');"
        "request.send(arguments[0]);"
        "return request.responseText;",
        json.dumps(CHAT),
    )
    return json.loads(raw)["id"]


def _stage_fixture():
    shutil.rmtree(STAGED_FIXTURE, ignore_errors=True)
    shutil.copytree(FIXTURE_DIRECTORY, STAGED_FIXTURE)


class TestGalaxyAIChatPlugin(SeleniumIntegrationTestCase):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        _stage_fixture()
        config["ai_chat_plugin"] = FIXTURE

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(STAGED_FIXTURE, ignore_errors=True)

    def _fixture(self):
        return self.execute_script(
            "return document.querySelector('chat-fixture') && window.__fixture ? JSON.stringify(window.__fixture) : null;"
        )

    def _wait_for_fixture(self, condition, message):
        state = None
        for _ in range(60):
            raw = self._fixture()
            state = json.loads(raw) if raw else None
            if state and condition(state):
                return state
            time.sleep(0.5)
        raise AssertionError(f"{message}; the fixture has {state}")

    def _route(self, path):
        self.execute_script(
            "history.pushState({}, '', arguments[0]); window.dispatchEvent(new PopStateEvent('popstate'));", path
        )

    def _path(self):
        return self.execute_script("return window.location.pathname;")

    @selenium_test
    def test_hosts_the_configured_plugin_and_keeps_it_running(self):
        self.home()
        self.components.galaxyai.activity.wait_for_and_click()
        state = self._wait_for_fixture(lambda s: True, "the plugin did not mount")
        assert state["config"] == {"view": "chat"}
        self.wait_for_selector_absent_or_hidden(".galaxyai-container")
        assert self.execute_script("return document.querySelector('.plugin-chat-body chat-fixture') !== null;")
        self.execute_script("document.querySelector('chat-fixture').__kept = 'kept';")

        self._route("/galaxyai/new?q=Count%20my%20reads")
        state = self._wait_for_fixture(lambda s: len(s["commands"]) == 1, "the question did not arrive")
        assert state["commands"] == [{"from": "galaxy", "type": "ask", "question": "Count my reads"}]

        chat_id = _create_chat(self)
        self.execute_script("window.confirm = () => true;")
        self._route(f"/galaxyai/{chat_id}")
        state = self._wait_for_fixture(lambda s: len(s["commands"]) == 2, "the chat did not open")
        assert state["commands"][1] == {"from": "galaxy", "type": "open", "exchange_id": chat_id}
        assert self._path() == f"/galaxyai/{chat_id}"

        self.wait_for_selector_visible("[title='Dock to side panel']").click()
        self.wait_for_selector_visible("#chat-panel")
        assert self._path() == "/"
        self.wait_for_selector_visible("[title='Dock to bottom panel']").click()
        self.wait_for_selector_visible(".chat-panel-body")
        assert self.execute_script("return document.querySelectorAll('chat-fixture').length;") == 1
        kept = self.execute_script("return document.querySelector('chat-fixture').__kept;")
        assert kept == "kept", "the plugin's element was replaced"
        assert self.execute_script("return document.querySelector('.chat-panel-body chat-fixture') !== null;")
        assert json.loads(self._fixture())["starts"] == 1, "the plugin started again"


class TestGalaxyAIWithoutPlugin(SeleniumIntegrationTestCase):
    ensure_registered = True

    @selenium_test
    def test_native_chat_shows_a_plugin_chat_and_explains_it_continues_there(self):
        self.home()
        chat_id = _create_chat(self)
        self.get(f"galaxyai/{chat_id}")
        self.wait_for_selector_visible(".galaxyai-container")
        self.wait_for_xpath_visible("//*[contains(@class, 'galaxyai-container')]//*[contains(text(), 'HISAT2.')]")
        assert self.execute_script("return document.querySelector('chat-fixture');") is None
        chat_input = self.wait_for_selector_visible("#chat-input")
        chat_input.send_keys("And now?")
        self.send_enter(chat_input)
        self.wait_for_xpath_visible(
            "//*[contains(@class, 'galaxyai-container')]//*[contains(text(), 'continues there')]"
        )

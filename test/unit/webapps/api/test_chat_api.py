"""Unit tests for ChatAPI's job-linked chat and Learning Mode endpoints."""

import json
from typing import Any
from unittest import mock

import pytest

from galaxy.exceptions import ConfigDoesNotAllowException
from galaxy.managers.chat import ChatManager
from galaxy.managers.learning_state import LearningStateManager
from galaxy.managers.tutor_analytics import TutorAnalyticsManager
from galaxy.schema.agents import (
    AgentResponse,
    LearningStateUpdate,
    TutorModeToggle,
)
from galaxy.schema.schema import ChatPayload
from galaxy.webapps.galaxy.api.chat import ChatAPI


def _chat_api(**overrides: Any) -> ChatAPI:
    """Build ChatAPI the way the DI container would, with real managers where they're cheap."""
    deps: dict[str, Any] = {
        "config": mock.Mock(),
        "chat_manager": ChatManager(),
        "job_manager": mock.Mock(),
        "agent_service": mock.Mock(),
        "workflow_manager": mock.Mock(),
        "learning_state_manager": LearningStateManager(),
        "tutor_analytics_manager": TutorAnalyticsManager(),
    }
    deps.update(overrides)
    return ChatAPI(**deps)


def _make_trans(user_id=1):
    """Create a mock ProvidesUserContext."""
    trans = mock.Mock()
    trans.user = mock.Mock()
    trans.user.id = user_id
    trans.sa_session = mock.Mock()
    return trans


class _FakeChatExchange:
    """Lightweight stand-in that avoids SQLAlchemy instrumentation."""

    # Class-level Mocks stand in for SQLAlchemy column expressions (e.g. ChatExchange.id.desc());
    # typed Any so tests can also assign real ids to instances (e.g. exchange.id = 31).
    user_id: Any = mock.Mock()
    job_id: Any = mock.Mock()
    page_id: Any = mock.Mock()
    id: Any = mock.Mock()

    def __init__(self, user=None, job_id=None, page_id=None, message=None, **kw):
        self.user = user
        self.job_id = job_id
        self.page_id = page_id
        self.messages = []
        if message:
            self.add_message(message)

    def add_message(self, message):
        self.messages.append(_FakeChatExchangeMessage(message=message))


class _FakeChatExchangeMessage:
    def __init__(self, message, feedback=None):
        self.message = message
        self.feedback = feedback


def _chainable_select(*args, **kwargs):
    """Return a mock that supports chained .where().order_by().limit()."""
    m = mock.Mock()
    m.where.return_value = m
    m.order_by.return_value = m
    m.limit.return_value = m
    return m


@pytest.fixture(autouse=True)
def _patch_models(monkeypatch):
    """Replace real SQLAlchemy models with lightweight fakes."""
    monkeypatch.setattr("galaxy.managers.chat.ChatExchange", _FakeChatExchange)
    monkeypatch.setattr("galaxy.managers.chat.ChatExchangeMessage", _FakeChatExchangeMessage)
    monkeypatch.setattr("galaxy.managers.chat.select", _chainable_select)


class TestJobChatPersistence:
    @pytest.fixture
    def job_chat(self, monkeypatch):
        trans = _make_trans()

        def assign_identity(obj):
            if isinstance(obj, _FakeChatExchange):
                obj.id = 31
            else:
                obj.chat_exchange_id = 31
                obj.create_time = None

        trans.sa_session.add.side_effect = assign_identity

        job_manager = mock.Mock()
        job_manager.get_accessible_job.return_value = mock.Mock(id=7)
        api = _chat_api(job_manager=job_manager)

        get_mock = mock.Mock(return_value=None)
        monkeypatch.setattr(api.chat_manager, "get", get_mock)

        delegate = mock.AsyncMock(
            return_value=AgentResponse(
                content="Check which reference index was selected.",
                agent_type="teaching_assistant",
                confidence="high",
            )
        )
        monkeypatch.setattr(api, "_get_agent_response_full", delegate)
        return api, trans, get_mock, delegate

    async def test_job_tutor_round_trip_preserves_attribution_and_feedback(self, job_chat):
        api, trans, get_mock, delegate = job_chat
        payload = ChatPayload(query="Help me understand this failed job")
        result = await api.query(job_id=7, payload=payload, agent_type="auto", trans=trans, user=trans.user)

        assert result.error_code == 0
        exchange = trans.sa_session.add.call_args_list[0].args[0]
        trans.sa_session.commit.assert_called_once()
        stored = json.loads(exchange.messages[0].message)
        assert stored["query"] == payload.query
        assert stored["agent_type"] == "teaching_assistant"
        assert stored["agent_response"] == result.agent_response.model_dump()

        get_mock.return_value = exchange
        cached = await api.query(job_id=7, payload=payload, agent_type="auto", trans=trans, user=trans.user)
        assert cached.response == result.response
        assert cached.agent_response == result.agent_response
        assert cached.exchange_id == result.exchange_id
        delegate.assert_awaited_once()

        exchange.messages[0].feedback = 0
        analytics = TutorAnalyticsManager()
        assert analytics._aggregate(exchange.messages, [])["tutor_feedback"]["negative"] == 1
        assert analytics._downvoted_tutor_queries(exchange.messages) == [payload.query]
        with mock.patch.object(api.chat_manager, "get_exchange_by_id", return_value=exchange):
            messages = api.chat_manager.get_exchange_messages(trans, exchange.id)
        assert messages[0]["content"] == payload.query
        assert messages[1]["agent_type"] == "teaching_assistant"
        assert messages[1]["content"] == result.response

    @pytest.mark.parametrize("content", ["Check the reference index.", '{"response": "An example"}', "[]", "null"])
    async def test_cached_legacy_job_responses_remain_plain_text(self, job_chat, content):
        api, trans, get_mock, delegate = job_chat
        exchange = _FakeChatExchange(message=content)
        exchange.id = 31
        get_mock.return_value = exchange

        result = await api.query(
            job_id=7, payload=ChatPayload(query="Why did this fail?"), agent_type="auto", trans=trans, user=trans.user
        )

        assert result.response == content
        assert result.agent_response is None
        delegate.assert_not_awaited()


class TestLearningModeFlag:
    """The tutor endpoints refuse requests unless the admin turned Learning Mode on."""

    def _api(self, enabled):
        return _chat_api(config=mock.Mock(enable_learning_mode=enabled))

    @pytest.mark.parametrize(
        "call",
        [
            lambda api, trans: api.get_tutor_state(trans=trans, user=trans.user),
            lambda api, trans: api.update_tutor_state(
                payload=LearningStateUpdate(tutor_mode_enabled=True), trans=trans, user=trans.user
            ),
            lambda api, trans: api.toggle_tutor_mode(
                payload=TutorModeToggle(enabled=True), trans=trans, user=trans.user
            ),
            lambda api, trans: api.get_tutor_analytics(trans=trans),
        ],
    )
    def test_tutor_endpoints_refuse_when_learning_mode_is_off(self, call):
        trans = _make_trans()
        trans.user.preferences = mock.MagicMock()
        with pytest.raises(ConfigDoesNotAllowException):
            call(self._api(False), trans)
        trans.user.preferences.__setitem__.assert_not_called()

    def test_tutor_state_is_served_when_learning_mode_is_on(self):
        trans = _make_trans()
        trans.user.preferences = {}
        assert self._api(True).get_tutor_state(trans=trans, user=trans.user).tutor_mode_enabled is False

    def test_state_update_only_takes_user_settable_fields(self):
        trans = _make_trans()
        trans.user.preferences = {}
        # Counters are server-derived; a user must not be able to forge their own progress.
        payload = LearningStateUpdate.model_validate({"scaffolding_level": 4, "interaction_count": 999})

        state = self._api(True).update_tutor_state(payload=payload, trans=trans, user=trans.user)

        assert state.scaffolding_level == 4
        assert state.interaction_count == 0
        with pytest.raises(ValueError):
            LearningStateUpdate(scaffolding_level=9)

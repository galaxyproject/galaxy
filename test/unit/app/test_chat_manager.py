"""Unit tests for ChatManager page-scoped methods."""

import json
from unittest import mock

import pytest

from galaxy.managers.chat import ChatManager


def _make_trans(user_id=1):
    """Create a mock ProvidesUserContext."""
    trans = mock.Mock()
    trans.user = mock.Mock()
    trans.user.id = user_id
    trans.sa_session = mock.Mock()
    return trans


class _FakeChatExchange:
    """Lightweight stand-in that avoids SQLAlchemy instrumentation."""

    user_id = mock.Mock()
    job_id = mock.Mock()
    page_id = mock.Mock()
    id = mock.Mock()

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


class TestCreatePageChat:
    def test_creates_exchange_with_page_id(self):
        mgr = ChatManager()
        trans = _make_trans()

        exchange = mgr.create_page_chat(trans, page_id=42, query="Describe the datasets", response_data="OK")

        assert exchange.page_id == 42
        assert exchange.job_id is None
        assert len(exchange.messages) == 1

        msg_data = json.loads(exchange.messages[0].message)
        assert msg_data["query"] == "Describe the datasets"
        assert msg_data["response"] == "OK"
        assert msg_data["agent_type"] == "page_assistant"

        trans.sa_session.add.assert_called()
        trans.sa_session.commit.assert_called_once()

    def test_creates_with_dict_response(self):
        mgr = ChatManager()
        trans = _make_trans()

        response = {"response": "I see 3 datasets", "agent_response": {"edit_mode": "section_patch"}}
        exchange = mgr.create_page_chat(trans, page_id=7, query="What's here?", response_data=response)

        msg_data = json.loads(exchange.messages[0].message)
        assert msg_data["response"] == "I see 3 datasets"
        assert msg_data["agent_response"] == {"edit_mode": "section_patch"}

    def test_default_agent_type(self):
        mgr = ChatManager()
        trans = _make_trans()

        exchange = mgr.create_page_chat(trans, page_id=1, query="hi", response_data="hello")
        msg_data = json.loads(exchange.messages[0].message)
        assert msg_data["agent_type"] == "page_assistant"

    def test_custom_agent_type(self):
        mgr = ChatManager()
        trans = _make_trans()

        exchange = mgr.create_page_chat(trans, page_id=1, query="hi", response_data="hello", agent_type="custom")
        msg_data = json.loads(exchange.messages[0].message)
        assert msg_data["agent_type"] == "custom"


class TestGetPageChatHistory:
    def test_queries_by_page_id(self):
        mgr = ChatManager()
        trans = _make_trans()

        mock_exchange = mock.Mock()
        trans.sa_session.execute.return_value.scalars.return_value.all.return_value = [mock_exchange]

        result = mgr.get_page_chat_history(trans, page_id=42)

        assert result == [mock_exchange]
        trans.sa_session.execute.assert_called_once()

    def test_empty_result(self):
        mgr = ChatManager()
        trans = _make_trans()
        trans.sa_session.execute.return_value.scalars.return_value.all.return_value = []

        result = mgr.get_page_chat_history(trans, page_id=99)
        assert result == []


class TestGetUserChatHistoryExcludesPage:
    def test_excludes_page_chats_by_default(self):
        mgr = ChatManager()
        trans = _make_trans()
        trans.sa_session.execute.return_value.scalars.return_value.all.return_value = []

        mgr.get_user_chat_history(trans)

        trans.sa_session.execute.assert_called_once()

    def test_includes_page_chats_when_asked(self):
        mgr = ChatManager()
        trans = _make_trans()
        trans.sa_session.execute.return_value.scalars.return_value.all.return_value = []

        mgr.get_user_chat_history(trans, include_page_chats=True)

        trans.sa_session.execute.assert_called_once()


class TestGetRoutingHistory:
    """get_routing_history returns the pydantic-ai history plus whether the last turn asked a
    clarifying question -- both from one fetch. The router uses the flag to re-include that turn
    when routing an otherwise-elliptical answer ("the second one")."""

    @staticmethod
    def _exchange_with(*messages):
        exchange = _FakeChatExchange()
        for message in messages:
            exchange.add_message(message if isinstance(message, str) else json.dumps(message))
        return exchange

    def _routing_history(self, mgr, trans, exchange):
        with mock.patch.object(mgr, "get_exchange_by_id", return_value=exchange):
            return mgr.get_routing_history(trans, 1)

    def test_true_when_last_response_is_clarification(self):
        mgr = ChatManager()
        trans = _make_trans()
        exchange = self._exchange_with(
            {"query": "help me", "response": "Tool or tutorial?", "agent_response": {"agent_type": "clarification"}},
        )
        history, responding = self._routing_history(mgr, trans, exchange)
        assert responding is True
        # The turn is reconstructed for routing context (user query + assistant response).
        assert len(history) == 2

    def test_false_for_normal_last_message(self):
        mgr = ChatManager()
        trans = _make_trans()
        exchange = self._exchange_with(
            {"query": "align reads", "response": "Use BWA", "agent_response": {"agent_type": "tool_recommendation"}},
        )
        _, responding = self._routing_history(mgr, trans, exchange)
        assert responding is False

    def test_only_the_last_message_counts(self):
        mgr = ChatManager()
        trans = _make_trans()
        # Earlier clarification, last is normal -> False
        stale = self._exchange_with(
            {"agent_response": {"agent_type": "clarification"}},
            {"agent_response": {"agent_type": "router"}},
        )
        assert self._routing_history(mgr, trans, stale)[1] is False
        # Earlier normal, last is clarification -> True
        fresh = self._exchange_with(
            {"agent_response": {"agent_type": "router"}},
            {"agent_response": {"agent_type": "clarification"}},
        )
        assert self._routing_history(mgr, trans, fresh)[1] is True

    def test_empty_when_no_exchange(self):
        mgr = ChatManager()
        trans = _make_trans()
        with mock.patch.object(mgr, "get_exchange_by_id", return_value=None):
            assert mgr.get_routing_history(trans, 999) == ([], False)

    def test_empty_for_no_messages(self):
        mgr = ChatManager()
        trans = _make_trans()
        with mock.patch.object(mgr, "get_exchange_by_id", return_value=_FakeChatExchange()):
            assert mgr.get_routing_history(trans, 1) == ([], False)

    def test_not_clarification_for_malformed_json(self):
        mgr = ChatManager()
        trans = _make_trans()
        exchange = self._exchange_with("not valid json{{{")
        _, responding = self._routing_history(mgr, trans, exchange)
        assert responding is False


class TestResolvePageFromInterfaceContext:
    """resolve_page_from_interface_context extracts and validates a page from
    an interface_context notebook payload, delegating access-check to
    get_accessible_page."""

    def _trans(self, decoded_id=99):
        trans = _make_trans()
        trans.security = mock.Mock()
        trans.security.decode_id.return_value = decoded_id
        return trans

    def test_returns_none_none_when_query_context_is_none(self):
        mgr = ChatManager()
        assert mgr.resolve_page_from_interface_context(_make_trans(), None) == (None, None)

    def test_returns_none_none_when_interface_context_absent(self):
        mgr = ChatManager()
        assert mgr.resolve_page_from_interface_context(_make_trans(), {"other_key": "value"}) == (None, None)

    def test_returns_none_none_when_context_type_is_not_notebook(self):
        mgr = ChatManager()
        trans = self._trans()
        ctx = {"interface_context": {"contextType": "tool", "pageId": "abc"}}
        assert mgr.resolve_page_from_interface_context(trans, ctx) == (None, None)

    def test_returns_none_none_when_page_id_missing(self):
        mgr = ChatManager()
        trans = self._trans()
        ctx = {"interface_context": {"contextType": "notebook"}}
        assert mgr.resolve_page_from_interface_context(trans, ctx) == (None, None)

    def test_returns_none_none_when_decode_raises(self):
        mgr = ChatManager()
        trans = self._trans()
        trans.security.decode_id.side_effect = Exception("bad id")
        ctx = {"interface_context": {"contextType": "notebook", "pageId": "invalid"}}
        assert mgr.resolve_page_from_interface_context(trans, ctx) == (None, None)

    def test_returns_page_id_and_page_obj_on_success(self):
        mgr = ChatManager()
        trans = self._trans(decoded_id=42)
        fake_page = mock.Mock()
        with mock.patch.object(mgr, "get_accessible_page", return_value=fake_page) as mock_get:
            ctx = {"interface_context": {"contextType": "notebook", "pageId": "encodedAbc"}}
            page_id, page_obj = mgr.resolve_page_from_interface_context(trans, ctx)

        assert page_id == 42
        assert page_obj is fake_page
        mock_get.assert_called_once_with(trans, 42)


class TestResponderAgentType:
    """The displayed agent_type should be the agent that actually answered (the nested
    agent_response), not the request type stored at the top level ("auto")."""

    def test_prefers_nested_response_agent_type(self):
        data = {"agent_type": "auto", "agent_response": {"agent_type": "error_analysis"}}
        assert ChatManager.responder_agent_type(data) == "error_analysis"

    def test_falls_back_to_top_level_when_no_response(self):
        data = {"agent_type": "gtn_training", "agent_response": None}
        assert ChatManager.responder_agent_type(data) == "gtn_training"

    def test_unknown_when_nothing_present(self):
        assert ChatManager.responder_agent_type({}) == "unknown"


class TestGetExchangeMessagesAttribution:
    """Reopening a conversation should badge each turn with the real responder, so a
    router handoff turn (persisted with top-level agent_type "auto") reloads as the
    specialist that actually answered."""

    @staticmethod
    def _exchange_for(message):
        msg = mock.Mock()
        msg.message = message
        msg.feedback = None
        msg.create_time = None
        exchange = _FakeChatExchange()
        exchange.messages = [msg]
        return exchange

    def _assistant_turn(self, message):
        mgr = ChatManager()
        exchange = self._exchange_for(message)
        with mock.patch.object(mgr, "get_exchange_by_id", return_value=exchange):
            messages = mgr.get_exchange_messages(_make_trans(), exchange_id=1)
        assistant = [m for m in messages if m["role"] == "assistant"]
        assert len(assistant) == 1
        return assistant[0]

    def test_handoff_turn_reloads_as_specialist(self):
        message = json.dumps(
            {
                "query": "why did my job fail?",
                "response": "Your tool hit an out-of-memory error.",
                "agent_type": "auto",
                "agent_response": {"agent_type": "error_analysis"},
            }
        )
        assert self._assistant_turn(message)["agent_type"] == "error_analysis"

    def test_falls_back_to_stored_type_without_response(self):
        message = json.dumps(
            {
                "query": "find me a tutorial",
                "response": "Here are some tutorials.",
                "agent_type": "gtn_training",
            }
        )
        assert self._assistant_turn(message)["agent_type"] == "gtn_training"

from ._framework import ApiTestCase

MAX_PLUGIN_CHAT_SIZE = 16 * 1024 * 1024

TURNS = [{"query": "Count my reads", "response": "There are 42."}]


def _document(text: str = "") -> dict:
    return {
        "olit_session": 1,
        "session": {"id": "s1", "title": "Ünïcødé ✓ 🧬"},
        "entries": [{"kind": "x", "data": {"float": 0.1, "null": None, "nested": [[1, [2]]], "text": text}}],
    }


class TestChatExchangesApi(ApiTestCase):
    def _save(self, document: dict, turns=None, exchange_id=None, agent_type="olit"):
        payload = {"agent_type": agent_type, "messages": TURNS if turns is None else turns, "document": document}
        if exchange_id is None:
            return self._post("chat/exchanges", data=payload, json=True)
        return self._put(f"chat/exchange/{exchange_id}", data=payload, json=True)

    def _create(self, document: dict) -> str:
        response = self._save(document)
        self._assert_status_code_is_ok(response)
        return response.json()["id"]

    def test_document_round_trip(self):
        document = _document("x" * 100000)
        exchange_id = self._create(document)
        response = self._get(f"chat/exchange/{exchange_id}/document")
        self._assert_status_code_is_ok(response)
        assert response.json() == {"id": exchange_id, "document": document}

    def test_update_replaces_document_and_turns(self):
        exchange_id = self._create(_document("first"))
        turns = TURNS + [{"query": "Plot them", "response": "Done."}]
        response = self._save(_document("second"), turns=turns, exchange_id=exchange_id)
        self._assert_status_code_is_ok(response)
        assert response.json()["id"] == exchange_id
        document = self._get(f"chat/exchange/{exchange_id}/document").json()["document"]
        assert document == _document("second")
        messages = self._get(f"chat/exchange/{exchange_id}/messages").json()
        assert [message["content"] for message in messages] == ["Count my reads", "There are 42.", "Plot them", "Done."]

    def test_update_leaves_another_plugins_chat_as_it_was(self):
        document = _document("mine")
        exchange_id = self._create(document)
        self._assert_status_code_is(self._save(_document("theirs"), exchange_id=exchange_id, agent_type="other"), 404)
        assert self._get(f"chat/exchange/{exchange_id}/document").json()["document"] == document

    def test_galaxy_ai_refuses_a_plugin_chat_before_answering(self):
        exchange_id = self._create(_document())
        response = self._post("chat", data={"query": "And now?", "exchange_id": exchange_id}, json=True)
        self._assert_status_code_is(response, 400)
        assert "continues there" in response.json()["err_msg"]

    def test_history_lists_saved_chats(self):
        exchange_id = self._create(_document())
        history = self._get("chat/history").json()
        listed = [item for item in history if item["id"] == exchange_id]
        assert len(listed) == 1
        assert listed[0]["agent_type"] == "olit"
        assert listed[0]["query"] == "Count my reads"

    def test_other_users_cannot_read_replace_or_delete(self):
        exchange_id = self._create(_document("mine"))
        with self._different_user():
            self._assert_status_code_is(self._get(f"chat/exchange/{exchange_id}/document"), 404)
            self._assert_status_code_is(self._save(_document("theirs"), exchange_id=exchange_id), 404)
            self._delete(f"chat/exchange/{exchange_id}")
            assert exchange_id not in [item["id"] for item in self._get("chat/history").json()]
        document = self._get(f"chat/exchange/{exchange_id}/document").json()["document"]
        assert document == _document("mine")

    def test_anonymous_users_cannot_save(self):
        with self._different_user(anon=True):
            response = self._save(_document())
            assert response.status_code in (400, 403)

    def test_refuses_invalid_saves(self):
        self._assert_status_code_is(self._save(_document(), turns=[]), 400)
        self._assert_status_code_is(self._save(_document(), agent_type="not a name"), 400)
        self._assert_status_code_is(self._get("chat/exchange/f2db41e1fa331b3e/document"), 400)

    def test_refuses_a_document_over_the_size_limit(self):
        response = self._save({"text": "x" * MAX_PLUGIN_CHAT_SIZE})
        self._assert_status_code_is(response, 400)
        assert "too large" in response.json()["err_msg"]

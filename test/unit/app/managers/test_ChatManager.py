from sqlalchemy import (
    event,
    inspect,
)

from galaxy.managers.chat import ChatManager
from .base import BaseTestCase


class TestChatManagerDocument(BaseTestCase):
    def test_history_does_not_load_documents(self):
        chat_manager = ChatManager()
        saved = chat_manager.save_document_chat(self.trans, "olit", [("question", "answer")], {"entries": ["turn"]})
        saved_id = saved.id
        self.trans.sa_session.expunge(saved)

        history = chat_manager.get_user_chat_history(self.trans)

        assert [exchange.id for exchange in history] == [saved_id]
        assert "document" in inspect(history[0]).unloaded
        assert chat_manager.get_document_chat(self.trans, saved_id).document == {"entries": ["turn"]}

    def test_document_checks_do_not_load_documents(self):
        chat_manager = ChatManager()
        saved = chat_manager.save_document_chat(self.trans, "olit", [("question", "answer")], {"entries": ["turn"]})
        saved_id = saved.id
        self.trans.sa_session.expunge(saved)
        statements: list[str] = []

        def record(conn, cursor, statement, *args):
            statements.append(statement)

        engine = self.trans.sa_session.get_bind()
        event.listen(engine, "before_cursor_execute", record)
        try:
            assert chat_manager.has_document(self.trans, saved_id)
            chat_manager.save_document_chat(
                self.trans, "olit", [("question", "answer")], {"entries": ["turn", "next"]}, exchange_id=saved_id
            )
        finally:
            event.remove(engine, "before_cursor_execute", record)

        assert not any("AS chat_exchange_document" in statement for statement in statements)
        assert chat_manager.get_document_chat(self.trans, saved_id).document == {"entries": ["turn", "next"]}

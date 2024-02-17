from galaxy.model.orm.engine_factory import set_sqlite_connect_args

SQLITE_URL = "sqlite://foo.db"
NON_SQLITE_URL = "foo://foo.db"


class TestSetSqliteConnectArgs:
    def test_engine_options_empty(self):
        engine_options = {}  # type: ignore[var-annotated]
        updated = set_sqlite_connect_args(engine_options, SQLITE_URL)
        assert updated == {"connect_args": {"check_same_thread": False}}

    def test_update_nonempty_engine_options(self):
        engine_options = {"foo": "some foo"}
        updated = set_sqlite_connect_args(engine_options, SQLITE_URL)
        assert len(updated) == 2
        assert updated["foo"] == "some foo"
        assert updated["connect_args"] == {"check_same_thread": False}

    def test_overwrite_connect_args(self):
        engine_options = {"foo": "some foo", "connect_args": {"check_same_thread": True}}
        updated = set_sqlite_connect_args(engine_options, SQLITE_URL)
        assert len(updated) == 2
        assert updated["foo"] == "some foo"
        assert updated["connect_args"] == {"check_same_thread": False}

    def test_update_nonempty_connect_args(self):
        engine_options = {"foo": "some foo", "connect_args": {"bar": "some bar"}}
        updated = set_sqlite_connect_args(engine_options, SQLITE_URL)
        assert len(updated) == 2
        assert updated["foo"] == "some foo"
        assert len(updated["connect_args"]) == 2
        assert updated["connect_args"]["check_same_thread"] is False
        assert updated["connect_args"]["bar"] == "some bar"

from galaxy.model.orm.engine_factory import set_sqlite_connect_args

SQLITE_URL = "sqlite://foo.db"
NON_SQLITE_URL = "foo://foo.db"


class TestSetSqliteConnectArgs:
    def test_engine_options_empty(self):
        engine_options = {}  # type: ignore[var-annotated]
        set_sqlite_connect_args(engine_options, SQLITE_URL)
        assert engine_options == {"connect_args": {"check_same_thread": False}}

    def test_update_nonempty_engine_options(self):
        engine_options = {"foo": "some foo"}
        set_sqlite_connect_args(engine_options, SQLITE_URL)
        assert len(engine_options) == 2
        assert engine_options["foo"] == "some foo"
        assert engine_options["connect_args"] == {"check_same_thread": False}  # type:ignore[comparison-overlap]

    def test_overwrite_connect_args(self):
        engine_options = {"foo": "some foo", "connect_args": {"check_same_thread": True}}
        set_sqlite_connect_args(engine_options, SQLITE_URL)
        assert len(engine_options) == 2
        assert engine_options["foo"] == "some foo"
        assert engine_options["connect_args"] == {"check_same_thread": False}

    def test_update_nonempty_connect_args(self):
        engine_options = {"foo": "some foo", "connect_args": {"bar": "some bar"}}
        set_sqlite_connect_args(engine_options, SQLITE_URL)
        assert len(engine_options) == 2
        assert engine_options["foo"] == "some foo"
        assert len(engine_options["connect_args"]) == 2
        assert engine_options["connect_args"]["check_same_thread"] is False  # type:ignore[index]
        assert engine_options["connect_args"]["bar"] == "some bar"  # type:ignore[index]

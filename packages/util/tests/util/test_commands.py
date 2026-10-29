import os

from galaxy.util.commands import new_clean_env


def test_new_clean_env() -> None:
    saved_environ = os.environ.copy()
    os.environ["FOO"] = "foo"
    os.environ.pop("TMPDIR", None)
    try:
        clean_env = new_clean_env()
    finally:
        os.environ.clear()
        os.environ.update(saved_environ)
    assert "FOO" not in clean_env
    for k in ("HOME", "PATH"):
        if k in saved_environ:
            assert clean_env[k] == saved_environ[k]
    assert clean_env["LC_CTYPE"].endswith("UTF-8")
    assert clean_env["TMPDIR"]

def pytest_configure(config):
    try:
        import sqlalchemy.exc  # noqa: F401
    except ImportError:
        pass
    else:
        config.addinivalue_line("filterwarnings", "error::sqlalchemy.exc.SAWarning")

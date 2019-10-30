def pytest_unconfigure(config):
    try:
        # This needs to be run if no test were run.
        from .test_config_defaults import DRIVER
        DRIVER.tear_down()
        print("Galaxy test driver shutdown succesfull")
    except Exception:
        pass

def pytest_unconfigure(config):
    try:
        # This needs to be run if no test were run.
        from .test_toolbox_pytest import DRIVER

        DRIVER.tear_down()
        print("Galaxy test driver shutdown successful")
    except Exception:
        pass

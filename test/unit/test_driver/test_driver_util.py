from galaxy_test.driver.driver_util import attempt_ports


def test_attempt_ports():
    port = int(attempt_ports())
    assert port >= 8000 and port <= 10000

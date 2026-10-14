from galaxy.config import GalaxyAppConfiguration


def test_allowed_login_redirect_hosts_are_normalized():
    hosts = " Tools.Example.org, portal.example.org:443,,data.example.org:8443 "
    assert GalaxyAppConfiguration._parse_allowed_login_redirect_hosts(hosts) == [
        "tools.example.org",
        "portal.example.org",
        "data.example.org:8443",
    ]


def test_allowed_login_redirect_hosts_ignore_urls():
    hosts = "https://tools.example.org,tools.example.org/path,user@tools.example.org,portal.example.org"
    assert GalaxyAppConfiguration._parse_allowed_login_redirect_hosts(hosts) == ["portal.example.org"]

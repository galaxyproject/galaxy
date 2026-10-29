from galaxy.config import GalaxyAppConfiguration


def test_allowed_login_redirect_hosts_are_normalized():
    hosts = " Tools.Example.org, portal.example.org:443,,data.example.org:8443,[2001:DB8::1]:443,[::1]:8443 "
    assert GalaxyAppConfiguration._parse_allowed_login_redirect_hosts(hosts) == [
        "tools.example.org",
        "portal.example.org",
        "data.example.org:8443",
        "[2001:db8::1]",
        "[::1]:8443",
    ]


def test_allowed_login_redirect_hosts_ignore_entries_that_are_not_hosts():
    hosts = (
        "https://tools.example.org,tools.example.org/path,user@tools.example.org,*.example.org,a b,portal.example.org"
    )
    assert GalaxyAppConfiguration._parse_allowed_login_redirect_hosts(hosts) == ["portal.example.org"]


def test_allowed_login_redirect_hosts_ignore_entries_that_can_never_match(caplog):
    hosts = "::1,2001:db8::1,tools.example.org:,tools.example.org:https,[::1,portal.example.org"
    assert GalaxyAppConfiguration._parse_allowed_login_redirect_hosts(hosts) == ["portal.example.org"]
    assert caplog.text.count("Ignoring allowed_login_redirect_hosts entry") == 5

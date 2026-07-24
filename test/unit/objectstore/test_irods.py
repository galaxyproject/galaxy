import os
import ssl
import time

import pytest

from galaxy.objectstore.irods import (
    _IRODS_RETRY_ATTEMPTS,
    _retry_on_connection_error,
    parse_config_xml,
)
from galaxy.util import parse_xml

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

CONFIG_FILE_NAME = "irods_object_store_conf.xml"
CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, CONFIG_FILE_NAME)

CONFIG_FILE_NAME_NO_EXTRA_DIR = "irods_object_store_conf_no_extra_dir.xml"
CONFIG_FILE_NO_EXTRA_DIR = os.path.join(SCRIPT_DIRECTORY, CONFIG_FILE_NAME_NO_EXTRA_DIR)

CONFIG_FILE_NAME_NO_AUTH = "irods_object_store_conf_no_auth.xml"
CONFIG_FILE_NO_AUTH = os.path.join(SCRIPT_DIRECTORY, CONFIG_FILE_NAME_NO_AUTH)

CONFIG_FILE_NAME_SSL = "irods_object_store_conf_ssl.xml"
CONFIG_FILE_SSL = os.path.join(SCRIPT_DIRECTORY, CONFIG_FILE_NAME_SSL)

CONFIG_FILE_NAME_LOGICAL_PATH = "irods_object_store_conf_logical_path.xml"
CONFIG_FILE_LOGICAL_PATH = os.path.join(SCRIPT_DIRECTORY, CONFIG_FILE_NAME_LOGICAL_PATH)


def test_parse_valid_config_xml():
    tree = parse_xml(CONFIG_FILE)
    root = tree.getroot()
    config = parse_config_xml(root)

    assert config["auth"]["username"] == "rods"
    assert config["auth"]["password"] == "rods"
    assert config["resource"]["name"] == "demoResc"
    assert config["zone"]["name"] == "tempZone"
    assert config["connection"]["host"] == "localhost"
    assert config["connection"]["port"] == 1247
    assert config["connection"]["timeout"] == 30
    assert config["connection"]["refresh_time"] == 300
    assert config["connection"]["connection_pool_monitor_interval"] == 3600
    assert config["cache"]["path"] == "database/object_store_cache"
    assert config["cache"]["size"] == 1000
    assert config["extra_dirs"][0]["type"] == "job_work"
    assert config["extra_dirs"][0]["path"] == "database/job_working_directory_irods"
    assert config["extra_dirs"][1]["type"] == "temp"
    assert config["extra_dirs"][1]["path"] == "database/tmp_irods"


def test_parse_config_xml_ssl():
    tree = parse_xml(CONFIG_FILE_SSL)
    root = tree.getroot()
    config = parse_config_xml(root)

    assert config["ssl"]["client_server_negotiation"] == "request_server_negotiation"
    assert config["ssl"]["client_server_policy"] == "CS_NEG_REQUIRE"
    assert config["ssl"]["encryption_algorithm"] == "AES-256-CBC"
    assert config["ssl"]["encryption_key_size"] == 32
    assert config["ssl"]["encryption_num_hash_rounds"] == 16
    assert config["ssl"]["encryption_salt_size"] == 8
    assert config["ssl"]["ssl_verify_server"] == "cert"
    assert config["ssl"]["ssl_ca_certificate_file"] == "/etc/irods/ssl/irods.crt"


def test_parse_config_xml_logical_path():
    tree = parse_xml(CONFIG_FILE_LOGICAL_PATH)
    root = tree.getroot()
    config = parse_config_xml(root)

    assert config["logical"]["path"] == "/tempZone/home/rods"


def test_parse_config_xml_no_extra_dir():
    tree = parse_xml(CONFIG_FILE_NO_EXTRA_DIR)
    root = tree.getroot()
    with pytest.raises(Exception, match="No extra_dir element in config XML tree"):
        parse_config_xml(root)


def test_parse_config_xml_no_auth():
    tree = parse_xml(CONFIG_FILE_NO_AUTH)
    root = tree.getroot()
    with pytest.raises(Exception, match="No auth element in config XML tree"):
        parse_config_xml(root)


def _make_flaky(exc, fail_times):
    calls = {"n": 0}

    @_retry_on_connection_error
    def op(_self):
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise exc
        return "ok"

    return op, calls


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_: None)


def test_retry_recovers_from_transient_error():
    op, calls = _make_flaky(ssl.SSLEOFError("handshake"), fail_times=_IRODS_RETRY_ATTEMPTS - 1)
    assert op(object()) == "ok"
    assert calls["n"] == _IRODS_RETRY_ATTEMPTS


def test_retry_gives_up_after_max_attempts():
    op, calls = _make_flaky(ssl.SSLEOFError("handshake"), fail_times=_IRODS_RETRY_ATTEMPTS)
    with pytest.raises(ssl.SSLError):
        op(object())
    assert calls["n"] == _IRODS_RETRY_ATTEMPTS


def test_no_retry_on_success():
    op, calls = _make_flaky(ssl.SSLEOFError("handshake"), fail_times=0)
    assert op(object()) == "ok"
    assert calls["n"] == 1


def test_no_retry_on_unrelated_error():
    op, calls = _make_flaky(ValueError("boom"), fail_times=1)
    with pytest.raises(ValueError):
        op(object())
    assert calls["n"] == 1

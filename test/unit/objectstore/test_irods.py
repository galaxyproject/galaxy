import os

import pytest

from galaxy.objectstore.irods import parse_config_xml
from galaxy.util import parse_xml

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

CONFIG_FILE_NAME = "irods_object_store_conf.xml"
CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, CONFIG_FILE_NAME)

CONFIG_FILE_NAME_NO_EXTRA_DIR = "irods_object_store_conf_no_extra_dir.xml"
CONFIG_FILE_NO_EXTRA_DIR = os.path.join(SCRIPT_DIRECTORY, CONFIG_FILE_NAME_NO_EXTRA_DIR)

CONFIG_FILE_NAME_NO_AUTH = "irods_object_store_conf_no_auth.xml"
CONFIG_FILE_NO_AUTH = os.path.join(SCRIPT_DIRECTORY, CONFIG_FILE_NAME_NO_AUTH)


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
    assert config["cache"]["path"] == "database/object_store_cache"
    assert config["cache"]["size"] == 1000
    assert config["extra_dirs"][0]["type"] == "job_work"
    assert config["extra_dirs"][0]["path"] == "database/job_working_directory_irods"
    assert config["extra_dirs"][1]["type"] == "temp"
    assert config["extra_dirs"][1]["path"] == "database/tmp_irods"


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

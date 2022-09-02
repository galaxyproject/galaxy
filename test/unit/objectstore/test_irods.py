import os
import tempfile
import time
import threading

import pytest

from galaxy.objectstore import get_cache_size_files, ConcreteObjectStore, ONE_GIGA_BYTE
from galaxy.objectstore.irods import parse_config_xml
from galaxy.util import parse_xml
from galaxy.util.sleeper import Sleeper

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
    assert config["cache"]["size"] == 1
    assert config["cache_monitor"]["enabled"]
    assert config["cache_monitor"]["cache_limit"] == 0.6
    assert config["cache_monitor"]["interval"] == 30
    assert config["cache_monitor"]["startup_delay"] == 3
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


def test_cache_monitor():
    # Create a temporary directory for cache
    cache_dir = tempfile.TemporaryDirectory()

    # Create 12 file of size 100MB in cache
    # This is to exceed the 1 GB cache limit
    NUM_FILES = 12
    FILE_SIZE_MB = 100 * 1024 * 1024
    for idx in range(NUM_FILES):
        with open(os.path.join(cache_dir.name, "a_file_" + str(idx)), "wb") as f:
            f.write(str.encode("0") * FILE_SIZE_MB)

    # Confirm total size and number of files in cache
    total_size, file_list = get_cache_size_files(cache_dir.name)
    assert total_size == NUM_FILES * FILE_SIZE_MB
    assert len(file_list) == NUM_FILES

    # Parse irods config file
    tree = parse_xml(CONFIG_FILE)
    root = tree.getroot()
    config = parse_config_xml(root)

    # Setup cache monitor argument dictionary
    cache_monitor_args = {
        "cache_monitor_cache_limit": config["cache_monitor"]["cache_limit"],
        "cache_monitor_interval": config["cache_monitor"]["interval"],
        "cache_monitor_startup_delay": config["cache_monitor"]["startup_delay"],
        "staging_path": cache_dir.name,
        "cache_size": config["cache"]["size"],
    }

    # This Event object is initialized to False
    # It is set to True in shutdown(), causing
    # the cache monitor thread to return/terminate
    stop_cache_monitor_event = threading.Event()
    # Helper for interruptable sleep
    sleeper = Sleeper()

    # Pass the Event object, the sleeper object, and the cache monitor argument dictionary
    # to the cache_monitor method
    args = (stop_cache_monitor_event, sleeper)
    cache_monitor_thread = threading.Thread(
        target=ConcreteObjectStore._cache_monitor, args=args, kwargs=cache_monitor_args, name="CacheMonitorThread"
    )
    cache_monitor_thread.start()

    # Wait startup_delay + interval seconds, for cache monitor to
    # reclaim cache space. Then get the number of the files and their
    # total size to confirm cache monitor has ran successfully
    wait_time = config["cache_monitor"]["startup_delay"] + config["cache_monitor"]["interval"]
    time.sleep(wait_time)

    # Confirm cache monitor has deleted files in cache and total size
    # is now cache_limit percentage of cache size (say, 06 of 1GB, that is 600MB)
    total_size, file_list = get_cache_size_files(cache_dir.name)
    new_cache_size = config["cache"]["size"] * config["cache_monitor"]["cache_limit"] * ONE_GIGA_BYTE
    assert total_size < NUM_FILES * FILE_SIZE_MB
    assert len(file_list) < NUM_FILES
    assert total_size <= new_cache_size
    assert len(file_list) == int(new_cache_size / FILE_SIZE_MB)

    # Set the event object so the cache monitor thread terminates
    stop_cache_monitor_event.set()
    # Wait for the cache monitor thread to join before ending the test
    cache_monitor_thread.join()

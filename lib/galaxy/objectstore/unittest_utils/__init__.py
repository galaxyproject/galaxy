"""Utilities for configuring and using objectstores in unit tests."""
import os
from io import StringIO
from shutil import rmtree
from string import Template
from tempfile import mkdtemp

import yaml

from galaxy import objectstore
from galaxy.util import XML

DISK_TEST_CONFIG = """<?xml version="1.0"?>
<object_store type="disk">
    <files_dir path="${temp_directory}/files1"/>
    <extra_dir type="temp" path="${temp_directory}/tmp1"/>
    <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
</object_store>
"""


DISK_TEST_CONFIG_YAML = """
type: disk
files_dir: "${temp_directory}/files1"
extra_dirs:
  - type: temp
    path: "${temp_directory}/tmp1"
  - type: job_work
    path: "${temp_directory}/job_working_directory1"
"""


class Config:
    def __init__(self, config_str=DISK_TEST_CONFIG, clazz=None, store_by="id"):
        self.temp_directory = mkdtemp()
        if config_str.startswith("<"):
            config_file = "store.xml"
        else:
            config_file = "store.yaml"
        self.write(config_str, config_file)
        config = MockConfig(self.temp_directory, config_file, store_by=store_by)
        if clazz is None:
            self.object_store = objectstore.build_object_store_from_config(config)
        elif config_file == "store.xml":
            self.object_store = clazz.from_xml(config, XML(config_str))
        else:
            self.object_store = clazz(config, yaml.safe_load(StringIO(config_str)))

    def __enter__(self):
        return self, self.object_store

    def __exit__(self, type, value, tb):
        rmtree(self.temp_directory)

    def write(self, contents, name):
        path = os.path.join(self.temp_directory, name)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        contents_template = Template(contents)
        expanded_contents = contents_template.safe_substitute(temp_directory=self.temp_directory)
        open(path, "w").write(expanded_contents)
        return path


class MockConfig:
    def __init__(self, temp_directory, config_file, store_by="id"):
        self.file_path = temp_directory
        self.object_store_config_file = os.path.join(temp_directory, config_file)
        self.object_store_check_old_style = False
        self.object_store_cache_path = os.path.join(temp_directory, "staging")
        self.object_store_store_by = store_by
        self.jobs_directory = temp_directory
        self.new_file_path = temp_directory
        self.umask = 0000
        self.gid = 1000


__all__ = [
    "Config",
    "MockConfig",
    "DISK_TEST_CONFIG",
    "DISK_TEST_CONFIG_YAML",
]

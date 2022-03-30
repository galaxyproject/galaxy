import os
import tempfile
from typing import Tuple

from galaxy.files import (
    ConfiguredFileSources,
    ConfiguredFileSourcesConfig,
)


class TestConfiguredFileSources(ConfiguredFileSources):
    def __init__(self, file_sources_config: ConfiguredFileSourcesConfig, conf_dict: dict, test_root: str):
        super().__init__(file_sources_config, conf_dict=conf_dict)
        self.test_root = test_root


def setup_root():
    tmp = os.path.realpath(tempfile.mkdtemp())
    root = os.path.join(tmp, "root")
    os.mkdir(root)
    return tmp, root


def write_file_fixtures(tmp: str, root: str) -> Tuple[str, str]:
    if not os.path.exists(root):
        os.mkdir(root)
    os.symlink(os.path.join(tmp, "b"), os.path.join(root, "unsafe"))
    with open(os.path.join(root, "a"), "w") as f:
        f.write("a\n")
    with open(os.path.join(tmp, "b"), "w") as f:
        f.write("b\n")

    subdir1 = os.path.join(root, "subdir1")
    os.mkdir(subdir1)
    with open(os.path.join(subdir1, "c"), "w") as f:
        f.write("c\n")

    subdir2 = os.path.join(subdir1, "subdir2")
    os.mkdir(subdir2)
    with open(os.path.join(subdir2, "d"), "w") as f:
        f.write("d\n")

    os.symlink(subdir1, os.path.join(root, "unsafe_dir"))
    return tmp, root

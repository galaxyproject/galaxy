import configparser
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class MyPyEntry:
    section_name: str
    package_name: str
    target: str


def main():
    config = configparser.ConfigParser()
    config.read("./mypy.ini")
    for section in config.sections():
        if not section.startswith("mypy-"):
            continue
        section_name = section
        package_name = section[len("mypy-") :]
        if not (package_name.startswith("galaxy.") or package_name.startswith("tool_shed")):
            continue
        if "*" in package_name:
            # Do not handle wild cards yet.
            continue
        entry = MyPyEntry(section_name, package_name, to_python_path(package_name))
        if entry.target is None:
            print(f"Warning section {entry.section_name} does not refer to existant files")


def to_python_path(package_name: str) -> Optional[str]:
    path = os.path.join("lib", package_name.replace(".", "/"))
    if os.path.exists(path + ".py"):
        path = f"{path}.py"
    else:
        index_path = os.path.join(path, "__init__.py")
        if os.path.exists(index_path):
            path = index_path
        else:
            path = None
    return path


if __name__ == "__main__":
    main()

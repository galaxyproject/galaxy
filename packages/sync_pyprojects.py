import configparser
import tomllib
from pathlib import Path
from string import Template

PACKAGES_DIR = Path(__file__).parent
WORKSPACE_ROOT_PYPROJECT = PACKAGES_DIR / "pyproject.toml"

PYPROJECT_TOML = Template(
    """[build-system]
build-backend = "setuptools.build_meta"
requires = ["setuptools"]

[project]
dynamic = [
    "authors",
    "dependencies",
    "description",
    "license",
    "optional-dependencies",
    "readme",
    "requires-python",
    "version",
]
name = "${project_name}"
"""
)


def get_workspace_members(pyproject_path: Path):
    pyproject_file = Path(pyproject_path)
    if not pyproject_file.exists():
        raise FileNotFoundError(f"{pyproject_path} not found.")

    data = tomllib.load(pyproject_file.open("rb"))
    try:
        members = data["tool"]["uv"]["workspace"]["members"]
        if not isinstance(members, list):
            raise ValueError("Expected 'members' to be a list.")
        return members
    except KeyError:
        raise KeyError("Could not find [tool.uv.workspace] members in pyproject.toml.")


def update_project(project_directory: Path):
    if not project_directory.exists():
        raise Exception(f"Skipping {project_directory}, not found.")
    setup_cfg = project_directory / "setup.cfg"
    if not setup_cfg.exists():
        raise Exception(f"No setup.cfg found in {project_directory}")

    config = configparser.ConfigParser()
    config.read(setup_cfg)
    try:
        project_name = config["metadata"]["name"]
        print(f"Project name in {setup_cfg}: {project_name}")
    except KeyError:
        print(f"No [metadata] section or 'name' field in {setup_cfg}")
    pyproject_path = project_directory / "pyproject.toml"
    with pyproject_path.open("w") as f:
        f.write(PYPROJECT_TOML.substitute(project_name=project_name))

    if "options.extras_require" in config:
        extra_requires = config["options.extras_require"]
        if "test" in extra_requires:
            print("'" + extra_requires["test"] + "'")


def main():
    members = get_workspace_members(WORKSPACE_ROOT_PYPROJECT)
    for member in members:
        update_project(PACKAGES_DIR / Path(member))


if __name__ == "__main__":
    main()

#!/usr/bin/env python

"""
searches for tests for packages in the bioconda-recipes repo and on Anaconda, looking in different file locations. If no test can be found for the specified version, it will look for tests for other versions of the same package.

A shallow search (default for singularity and conda generation scripts) just checks once on Anaconda for the specified version.
"""
import json
import logging
from glob import glob
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import yaml

from galaxy.util import requests

try:
    from jinja2 import Template
    from jinja2.exceptions import UndefinedError
except ImportError:
    Template = None  # type: ignore[assignment,misc]
    UndefinedError = Exception  # type: ignore[assignment,misc]

from galaxy.util import (
    check_github_api_response_rate_limit,
    unicodify,
)
from galaxy.util.commands import argv_to_str
from .util import (
    get_files_from_conda_package,
    MULLED_SOCKET_TIMEOUT,
    split_container_name,
)

INSTALL_JINJA_EXCEPTION = (
    "This mulled functionality required jinja2 but it is unavailable, install condatesting extras."
)


def get_commands_from_yaml(yaml_content: bytes) -> Optional[Dict[str, Any]]:
    """
    Parse tests from Conda's meta.yaml file contents
    """
    if Template is None:
        raise Exception(INSTALL_JINJA_EXCEPTION)
    package_tests = {}

    try:
        # we expect to get an input in bytes, so first decode to string; run the file through the jinja processing; load as yaml
        meta_yaml = yaml.safe_load(Template(yaml_content.decode("utf-8")).render())
    except (yaml.scanner.ScannerError, UndefinedError) as e:  # what about things like {{ compiler('cxx') }}
        logging.info(e, exc_info=True)
        return None
    try:
        if meta_yaml["test"]["commands"] != [None] and meta_yaml["test"]["commands"] is not None:
            package_tests["commands"] = meta_yaml["test"]["commands"]
    except (KeyError, TypeError):
        logging.info("Error reading commands")
    try:
        if meta_yaml["test"]["imports"] != [None] and meta_yaml["test"]["imports"] is not None:
            package_tests["imports"] = meta_yaml["test"]["imports"]
    except (KeyError, TypeError):
        logging.info("Error reading imports")

    if len(package_tests.get("commands", []) + package_tests.get("imports", [])) == 0:
        return None

    # need to know what scripting languages are needed to run the container
    package_tests["import_lang"] = "python -c"  # python by default
    try:
        requirements = list(meta_yaml["requirements"]["run"])
    except (KeyError, TypeError):
        logging.info("Error reading requirements", exc_info=True)
    else:
        for requirement in requirements:
            if requirement.split()[0] == "perl":
                package_tests["import_lang"] = "perl -e"
                break
            # elif ... :
            # other languages if necessary ... hopefully python and perl should suffice though
    return package_tests


def get_run_test(file: str) -> Dict[str, Any]:
    r"""
    Get tests from a run_test.sh file
    """
    package_tests = {}
    package_tests["commands"] = [file.replace("\n", " && ")]
    return package_tests


def get_anaconda_url(container, anaconda_channel="bioconda"):
    """
    Download tarball from anaconda for test
    """
    name = split_container_name(container)  # list consisting of [name, version, (build, if present)]
    return f"https://anaconda.org/{anaconda_channel}/{name[0]}/{name[1]}/download/linux-64/{'-'.join(name)}.tar.bz2"


def prepend_anaconda_url(url):
    """
    Take a partial url and prepend 'https://anaconda.org'
    """
    return f"https://anaconda.org{url}"


def get_test_from_anaconda(url: str) -> Optional[Dict[str, Any]]:
    """
    Given the URL of an anaconda tarball, return tests
    """
    content_dict = get_files_from_conda_package(
        url, ["info/recipe/meta.yaml", "info/recipe/meta.yaml.template", "info/recipe/run_test.sh"]
    )
    content = content_dict.get("info/recipe/meta.yaml", content_dict.get("info/recipe/meta.yaml.template"))
    if content:
        package_tests = get_commands_from_yaml(content)
        if package_tests:
            return package_tests
    if "info/recipe/run_test.sh" in content_dict:
        return get_run_test(unicodify(content_dict["info/recipe/run_test.sh"]))
    return None


def find_anaconda_versions(name, anaconda_channel="bioconda"):
    """
    Find a list of available anaconda versions for a given container name
    """
    r = requests.get(
        f"https://anaconda.org/{anaconda_channel}/{name}/files",
        timeout=MULLED_SOCKET_TIMEOUT,
    )
    r.raise_for_status()
    urls = []
    for line in r.text.splitlines():
        if "download/linux" in line:
            urls.append(line.split('"')[1])
    return urls


def open_recipe_file(file, recipes_path=None, github_repo="bioconda/bioconda-recipes"):
    """
    Open a file at a particular location and return contents as string
    """
    if recipes_path:
        return open(f"{recipes_path}/{file}").read()
    else:  # if no clone of the repo is available locally, download from GitHub
        r = requests.get(
            f"https://raw.githubusercontent.com/{github_repo}/master/{file}",
            timeout=MULLED_SOCKET_TIMEOUT,
        )
        if r.status_code == 404:
            raise OSError
        else:
            return r.content


def get_alternative_versions(filepath, filename, recipes_path=None, github_repo="bioconda/bioconda-recipes"):
    """
    Return files that match ``filepath/*/filename`` in the bioconda-recipes repository
    """
    if recipes_path:
        return [n.replace(f"{recipes_path}/", "") for n in glob(f"{recipes_path}/{filepath}/*/{filename}")]
    # else use the GitHub API:
    versions = []
    r = requests.get(
        f"https://api.github.com/repos/{github_repo}/contents/{filepath}",
        timeout=MULLED_SOCKET_TIMEOUT,
    )
    check_github_api_response_rate_limit(r)
    r.raise_for_status()
    for subfile in json.loads(r.text):
        if subfile["type"] == "dir":
            if (
                requests.get(
                    f"https://raw.githubusercontent.com/{github_repo}/master/{subfile['path']}/{filename}",
                    timeout=MULLED_SOCKET_TIMEOUT,
                ).status_code
                == 200
            ):
                versions.append(f"{subfile['path']}/{filename}")
    return versions


def try_a_func(func1, func2, param, container):
    """
    Try to perform a function (or actually a combination of two functions: first getting the file and then processing it)
    """
    try:
        result = func1(func2(*param))
    except OSError:
        return None
    if result:
        result["container"] = container
        return result


def deep_test_search(
    container, recipes_path=None, anaconda_channel="bioconda", github_repo="bioconda/bioconda-recipes"
):
    """
    Look in bioconda-recipes repo as well as anaconda for the tests, checking in multiple possible locations. If no test is found for the specified version, search if other package versions have a test available.
    """
    name = split_container_name(container)
    for f in [
        (
            get_commands_from_yaml,
            open_recipe_file,
            (f"recipes/{name[0]}/{name[1]}/meta.yaml", recipes_path, github_repo),
            container,
        ),
        (
            get_run_test,
            open_recipe_file,
            (f"recipes/{name[0]}/{name[1]}/run_test.sh", recipes_path, github_repo),
            container,
        ),
        (
            get_commands_from_yaml,
            open_recipe_file,
            (f"recipes/{name[0]}/meta.yaml", recipes_path, github_repo),
            container,
        ),
        (get_run_test, open_recipe_file, (f"recipes/{name[0]}/run_test.sh", recipes_path, github_repo), container),
        (get_test_from_anaconda, get_anaconda_url, (container, anaconda_channel), container),
    ]:
        result = try_a_func(*f)
        if result:
            return result

    versions = get_alternative_versions(f"recipes/{name[0]}", "meta.yaml", recipes_path, github_repo)
    for version in versions:
        result = try_a_func(get_commands_from_yaml, open_recipe_file, (version, recipes_path, github_repo), container)
        if result:
            return result

    versions = get_alternative_versions(f"recipes/{name[0]}", "run_test.sh", recipes_path, github_repo)
    for version in versions:
        result = try_a_func(get_run_test, open_recipe_file, (version, recipes_path, github_repo), container)
        if result:
            return result

    versions = find_anaconda_versions(name[0], anaconda_channel)
    for version in versions:
        result = try_a_func(get_test_from_anaconda, prepend_anaconda_url, (version,), container)
        if result:
            return result

    # if everything fails
    return {"container": container}


def main_test_search(
    container, recipes_path=None, deep=False, anaconda_channel="bioconda", github_repo="bioconda/bioconda-recipes"
):
    """
    Download tarball from anaconda for test
    """
    if deep:  # do a deep search
        return deep_test_search(container, recipes_path, anaconda_channel, github_repo)
    # else shallow
    result = try_a_func(get_test_from_anaconda, get_anaconda_url, (container, anaconda_channel), container)
    if result:
        return result
    return {"container": container}


def import_test_to_command_list(import_lang: str, import_: str) -> List[str]:
    if import_lang == "python -c":
        return ["python", "-c", f"import {import_}"]
    elif import_lang == "perl -e":
        return ["perl", "-e", f"use {import_}"]
    else:
        raise ValueError(f"Unsupported import_lang '{import_lang}'")


def hashed_test_search(
    container: str, recipes_path=None, deep=False, anaconda_channel="bioconda", github_repo="bioconda/bioconda-recipes"
) -> Dict[str, Any]:
    """
    Get test for hashed containers
    """
    package_tests: Dict[str, Any] = {"commands": [], "imports": [], "container": container, "import_lang": "python -c"}

    response = requests.get(
        f"https://raw.githubusercontent.com/BioContainers/multi-package-containers/master/combinations/{container}.tsv",
        timeout=MULLED_SOCKET_TIMEOUT,
    )
    response.raise_for_status()
    for line in response.text.splitlines():
        if not line.startswith("#"):
            break
    concatenated_targets = line.split("\t")[0]
    targets = concatenated_targets.split(",")
    packages = [target.split("=") for target in targets]

    containers = []
    for package in packages:
        r = requests.get(f"https://anaconda.org/bioconda/{package[0]}/files", timeout=MULLED_SOCKET_TIMEOUT)
        r.raise_for_status()
        p = "-".join(package)
        for line in r.text.split("\n"):
            # include only linux-64 builds since that is hardcoded in get_anaconda_url and the only target for container builds
            if p in line and "linux-64" in line:
                build = line.split(p)[1].split(".tar.bz2")[0]
                if build == "":
                    containers.append(f"{package[0]}:{package[1]}")
                else:
                    containers.append(f"{package[0]}:{package[1]}-{build}")
                break

    for container in containers:
        tests = main_test_search(container, recipes_path, deep, anaconda_channel, github_repo)
        package_tests["commands"] += tests.get("commands", [])  # not a very nice solution but probably the simplest
        # Given that this could be a mix of Python and Perl packages, translate imports to commands
        for imp in tests.get("imports", []):
            package_tests["commands"].append(argv_to_str(import_test_to_command_list(tests["import_lang"], imp)))

    return package_tests

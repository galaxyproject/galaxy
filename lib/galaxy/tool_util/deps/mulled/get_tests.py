#!/usr/bin/env python

"""
searches for tests for packages in the bioconda-recipes repo and on Anaconda, looking in different file locations. If no test can be found for the specified version, it will look for tests for other versions of the same package.

A shallow search (default for singularity and conda generation scripts) just checks once on Anaconda for the specified version.
"""
# import doctest
import json
import logging
import tarfile
from glob import glob

import requests
import yaml

try:
    from jinja2 import Template
    from jinja2.exceptions import UndefinedError
except ImportError:
    Template = None  # type: ignore[assignment,misc]
    UndefinedError = Exception  # type: ignore[assignment,misc]

from .util import (
    get_file_from_recipe_url,
    MULLED_SOCKET_TIMEOUT,
    split_container_name,
)

INSTALL_JINJA_EXCEPTION = (
    "This mulled functionality required jinja2 but it is unavailable, install condatesting extras."
)


def get_commands_from_yaml(yaml_content):
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
        else:  # python by default
            package_tests["import_lang"] = "python -c"
    return package_tests


def get_run_test(file):
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


def get_test_from_anaconda(url):
    """
    Given the URL of an anaconda tarball, return tests
    """
    try:
        tarball = get_file_from_recipe_url(url)
    except tarfile.ReadError:
        return None

    try:
        metafile = tarball.extractfile("info/recipe/meta.yaml")
    except (tarfile.ReadError, KeyError, TypeError):
        pass
    else:
        package_tests = get_commands_from_yaml(metafile.read())
        if package_tests:
            return package_tests

    # this part is perhaps unnecessary, but some of the older tarballs have a testfile with .yaml.template ext
    try:
        metafile = tarball.extractfile("info/recipe/meta.yaml.template")
    except (tarfile.ReadError, KeyError, TypeError):
        pass
    else:
        package_tests = get_commands_from_yaml(metafile)
        if package_tests:
            return package_tests

    # if meta.yaml was not present or there were no tests in it, try and get run_test.sh instead
    try:
        run_test = tarball.extractfile("info/recipe/run_test.sh")
        return get_run_test(run_test)
    except KeyError:
        logging.info("run_test.sh file not present.")
        return None


def find_anaconda_versions(name, anaconda_channel="bioconda"):
    """
    Find a list of available anaconda versions for a given container name
    """
    r = requests.get(f"https://anaconda.org/{anaconda_channel}/{name}/files", timeout=MULLED_SOCKET_TIMEOUT)
    urls = []
    for line in r.text.split("\n"):
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
            f"https://raw.githubusercontent.com/{github_repo}/master/{file}", timeout=MULLED_SOCKET_TIMEOUT
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
    r = json.loads(
        requests.get(
            f"https://api.github.com/repos/{github_repo}/contents/{filepath}", timeout=MULLED_SOCKET_TIMEOUT
        ).text
    )
    for subfile in r:
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


def hashed_test_search(
    container, recipes_path=None, deep=False, anaconda_channel="bioconda", github_repo="bioconda/bioconda-recipes"
):
    """
    Get test for hashed containers
    """
    package_tests = {"commands": [], "imports": [], "container": container, "import_lang": "python -c"}

    githubpage = requests.get(
        f"https://raw.githubusercontent.com/BioContainers/multi-package-containers/master/combinations/{container}.tsv",
        timeout=MULLED_SOCKET_TIMEOUT,
    )
    if githubpage.status_code == 200:
        packages = githubpage.text.split(",")  # get names of packages from github
        packages = [package.split("=") for package in packages]
    else:
        packages = []

    containers = []
    for package in packages:
        r = requests.get(f"https://anaconda.org/bioconda/{package[0]}/files", timeout=MULLED_SOCKET_TIMEOUT)
        p = "-".join(package)
        for line in r.text.split("\n"):
            if p in line:
                build = line.split(p)[1].split(".tar.bz2")[0]
                if build == "":
                    containers.append(f"{package[0]}:{package[1]}")
                else:
                    containers.append(f"{package[0]}:{package[1]}-{build}")
                break

    for container in containers:
        tests = main_test_search(container, recipes_path, deep, anaconda_channel, github_repo)
        package_tests["commands"] += tests.get("commands", [])  # not a very nice solution but probably the simplest
        for imp in tests.get("imports", []):
            package_tests["imports"].append(f"{tests['import_lang']} 'import {imp}'")

    return package_tests

from galaxy.tool_util.deps.mulled.get_tests import (
    deep_test_search,
    find_anaconda_versions,
    get_alternative_versions,
    get_anaconda_url,
    get_commands_from_yaml,
    get_run_test,
    get_test_from_anaconda,
    hashed_test_search,
    main_test_search,
    open_recipe_file,
    prepend_anaconda_url,
)
from galaxy.util import smart_str
from ..util import external_dependency_management

TEST_RECIPE = r"""
{% set name = "eagle" %}
package:
  name: '{{ name }}'
requirements:
  run:
    - python
    - flask
test:
  imports:
    - eagle
  commands:
    - eagle --help
"""


def test_get_commands_from_yaml():
    commands = get_commands_from_yaml(smart_str(TEST_RECIPE))
    assert commands["imports"] == ["eagle"]
    assert commands["commands"] == ["eagle --help"]
    assert commands["import_lang"] == "python -c"


def test_get_run_test():
    commands = get_run_test(' #!/bin/bash\npslScore 2> /dev/null || [[ "$?" == 255 ]]')
    assert commands["commands"] == [' #!/bin/bash && pslScore 2> /dev/null || [[ "$?" == 255 ]]']


@external_dependency_management
def test_get_anaconda_url():
    url = get_anaconda_url("samtools:1.7--1")
    assert url == "https://anaconda.org/bioconda/samtools/1.7/download/linux-64/samtools-1.7-1.tar.bz2"


def test_prepend_anaconda_url():
    url = prepend_anaconda_url("/bioconda/samtools/0.1.12/download/linux-64/samtools-0.1.12-2.tar.bz2")
    assert url == "https://anaconda.org/bioconda/samtools/0.1.12/download/linux-64/samtools-0.1.12-2.tar.bz2"


@external_dependency_management
def test_get_test_from_anaconda():
    tests = get_test_from_anaconda(
        "https://anaconda.org/bioconda/samtools/1.3.1/download/linux-64/samtools-1.3.1-5.tar.bz2"
    )
    assert tests["commands"] == ["samtools --help"]
    assert tests["import_lang"] == "python -c"


@external_dependency_management
def test_find_anaconda_versions():
    versions = find_anaconda_versions("2pg_cartesian")
    assert "/bioconda/2pg_cartesian/1.0.1/download/linux-64/2pg_cartesian-1.0.1-0.tar.bz2" in versions


@external_dependency_management
def test_open_recipe_file():
    recipe = open_recipe_file("recipes/samtools/1.1/meta.yaml")
    assert b"samtools" in recipe


@external_dependency_management
def test_get_alternative_versions():
    versions = get_alternative_versions("recipes/bamtools", "meta.yaml")
    assert versions == ["recipes/bamtools/2.3.0/meta.yaml"]


@external_dependency_management
def test_deep_test_search():
    tests = deep_test_search("abundancebin:1.0.1--0")
    assert tests["commands"] == ["command -v abundancebin", 'abundancebin &> /dev/null || [[ "$?" == "255" ]]']
    assert tests["container"] == "abundancebin:1.0.1--0"
    assert tests["import_lang"] == "python -c"


@external_dependency_management
def test_main_test_search():
    tests = main_test_search("abundancebin:1.0.1--0")
    assert tests["commands"] == ["command -v abundancebin", 'abundancebin &> /dev/null || [[ "$?" == "255" ]]']
    assert tests["container"] == "abundancebin:1.0.1--0"
    assert tests["import_lang"] == "python -c"


@external_dependency_management
def test_hashed_test_search():
    tests = hashed_test_search(
        "mulled-v2-0560a8046fc82aa4338588eca29ff18edab2c5aa:c17ce694dd57ab0ac1a2b86bb214e65fedef760e-0"
    )
    assert tests["commands"] == ["bamtools --help", "samtools --help"]
    assert (
        tests["container"]
        == "mulled-v2-0560a8046fc82aa4338588eca29ff18edab2c5aa:c17ce694dd57ab0ac1a2b86bb214e65fedef760e-0"
    )
    assert tests["import_lang"] == "python -c"
    assert tests["imports"] == []

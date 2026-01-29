import pytest

from galaxy.tool_util.deps.mulled.mulled_search import (
    CondaSearch,
    get_package_hash,
    GitHubSearch,
    QuaySearch,
    singularity_search,
)
from galaxy.util.unittest_utils import skip_unless_executable
from ..util import external_dependency_management


@external_dependency_management
def test_quay_search():
    t = QuaySearch("biocontainers")
    t.build_index()
    search1 = t.search_repository("adsfasdf", True)
    search2 = t.search_repository("bioconductor-gosemsim", True)
    assert search1 == []
    assert {"version": "2.2.0--0", "package": "bioconductor-gosemsim"} in search2


@external_dependency_management
@skip_unless_executable("conda")
def test_conda_search():
    t = CondaSearch("bioconda")
    search = t.get_json("asdfasdf")
    assert search == []
    search = t.get_json("bioconductor-gosemsim")
    assert all(r["package"] == "bioconductor-gosemsim" for r in search)


@external_dependency_management
def test_github_recipe_present():
    t = GitHubSearch()

    search_string2expected = {
        "adsfasdf": False,
        "bioconductor-gosemsim": True,
    }
    for search_string, expected in search_string2expected.items():
        try:
            is_recipe_present = t.recipe_present(search_string)
        except Exception as e:
            if "API rate limit" in str(e):
                pytest.skip("Hitting GitHub API rate limit")
            raise
        assert is_recipe_present is expected


@external_dependency_management
def test_get_package_hash():
    package_hash1 = get_package_hash(["bamtools", "samtools"], {})
    package_hash2 = get_package_hash(["bamtools", "samtools"], {"bamtools": "2.4.0", "samtools": "1.3.1"})
    package_hash3 = get_package_hash(["abricate", "abyss"], {"abricate": "0.4", "abyss": "2.0.1"})
    assert package_hash1["package_hash"] == "mulled-v2-0560a8046fc82aa4338588eca29ff18edab2c5aa"
    assert package_hash2["version_hash"] == "c17ce694dd57ab0ac1a2b86bb214e65fedef760e"
    assert package_hash2["package_hash"] == "mulled-v2-0560a8046fc82aa4338588eca29ff18edab2c5aa"
    assert package_hash3["version_hash"] == "e21d1262f064e1e01b6b9fad5bea117928f31b38"
    assert package_hash3["package_hash"] == "mulled-v2-cde36934a4704f448af44bf01deeae8d2832ca2e"


@external_dependency_management
def test_singularity_search():
    sing1 = singularity_search("mulled-v2-0560a8046fc82aa4338588eca29ff18edab2c5aa")
    sing1_versions = {result["version"] for result in sing1}
    assert {
        "c17ce694dd57ab0ac1a2b86bb214e65fedef760e-0",
        "f471ba33d45697daad10614c5bd25a67693f67f1-0",
        "fc33176431a4b9ef3213640937e641d731db04f1-0",
    }.issubset(sing1_versions)
    sing2 = singularity_search("mulled-v2-19fa9431f5863b2be81ff13791f1b00160ed0852")
    assert sing2 == []

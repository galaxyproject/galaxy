import pytest

from galaxy.tool_util.deps.mulled.mulled_search import (
    CondaSearch,
    get_package_hash,
    GitHubSearch,
    QuaySearch,
    run_command,
    singularity_search
)
from ..util import external_dependency_management


@external_dependency_management
def test_quay_search():
    t = QuaySearch("biocontainers")
    t.build_index()
    search1 = t.search_repository("adsfasdf", True)
    search2 = t.search_repository("bioconductor-gosemsim", True)
    assert search1 == []
    assert {'version': '2.2.0--0', 'package': 'bioconductor-gosemsim'} in search2


@external_dependency_management
@pytest.mark.skipif(run_command is None, reason="requires import from conda library")
def test_conda_search():
    t = CondaSearch('bioconda')
    search1 = t.get_json("asdfasdf")
    search2 = t.get_json("bioconductor-gosemsim")
    assert search1 == []
    assert search2['version'] == '2.2.0'
    assert search2['package'] == 'bioconductor-gosemsim'
    assert search2['build'] == '0'


@external_dependency_management
def test_github_search():
    t = GitHubSearch()
    search1 = t.process_json(t.get_json("adsfasdf"), "adsfasdf")
    search2 = t.process_json(t.get_json("bioconductor-gosemsim"), "bioconductor-gosemsim")
    assert search1 == []
    assert {'path': 'recipes/bioconductor-gosemsim/meta.yaml', 'name': 'meta.yaml'} in search2


@external_dependency_management
def test_get_package_hash():
    package_hash1 = get_package_hash(['bamtools', 'samtools'], {})
    package_hash2 = get_package_hash(['bamtools', 'samtools'], {'bamtools': '2.4.0', 'samtools': '1.3.1'})
    package_hash3 = get_package_hash(['abricate', 'abyss'], {'abricate': '0.4', 'abyss': '2.0.1'})
    assert package_hash1['package_hash'] == 'mulled-v2-0560a8046fc82aa4338588eca29ff18edab2c5aa'
    assert package_hash2['version_hash'] == 'c17ce694dd57ab0ac1a2b86bb214e65fedef760e'
    assert package_hash2['package_hash'] == 'mulled-v2-0560a8046fc82aa4338588eca29ff18edab2c5aa'
    assert package_hash3['version_hash'] == 'e21d1262f064e1e01b6b9fad5bea117928f31b38'
    assert package_hash3['package_hash'] == 'mulled-v2-cde36934a4704f448af44bf01deeae8d2832ca2e'


@external_dependency_management
def test_singularity_search():
    sing1 = singularity_search('mulled-v2-0560a8046fc82aa4338588eca29ff18edab2c5aa')
    sing1_versions = {result['version'] for result in sing1}
    assert {
        'c17ce694dd57ab0ac1a2b86bb214e65fedef760e-0',
        'f471ba33d45697daad10614c5bd25a67693f67f1-0',
        'fc33176431a4b9ef3213640937e641d731db04f1-0'}.issubset(sing1_versions)
    sing2 = singularity_search('mulled-v2-19fa9431f5863b2be81ff13791f1b00160ed0852')
    assert sing2 == []

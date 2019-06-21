import pytest

from galaxy.tools.deps.mulled.mulled_update_singularity_containers import docker_to_singularity, get_list_from_file, singularity_container_test
from galaxy.util import which


def test_get_list_from_file():
    from os import remove
    with open('/tmp/list_file.txt', 'w') as f:
        f.write('bbmap:36.84--0\nbiobambam:2.0.42--0\nconnor:0.5.1--py35_0\ndiamond:0.8.26--0\nedd:1.1.18--py27_0')
    assert get_list_from_file('/tmp/list_file.txt') == ['bbmap:36.84--0', 'biobambam:2.0.42--0', 'connor:0.5.1--py35_0', 'diamond:0.8.26--0', 'edd:1.1.18--py27_0']
    remove('/tmp/list_file.txt')


@pytest.mark.skipif(not which('singularity'), reason="requires singularity but singularity not on PATH")
def test_docker_to_singularity(tmp_path):
    tmp_dir = str(tmp_path)
    errors = docker_to_singularity('abundancebin:1.0.1--0', 'singularity', tmp_dir, no_sudo=True)
    assert errors is None
    assert tmp_path.joinpath('abundancebin:1.0.1--0').exists()


@pytest.mark.skipif(not which('singularity'), reason="requires singularity but singularity not on PATH")
def test_singularity_container_test(tmp_path):
    import os
    import shutil
    tmp_dir = str(tmp_path)
    os.mkdir('/tmp/singtest')
    for n in ['pybigwig:0.1.11--py36_0', 'samtools:1.0--1', 'yasm:1.3.0--0']:
        docker_to_singularity(n, 'singularity', tmp_dir, no_sudo=True)
    results = singularity_container_test({'pybigwig:0.1.11--py36_0': {'imports': ['pyBigWig'], 'commands': ['python -c "import pyBigWig; assert(pyBigWig.numpy == 1); assert(pyBigWig.remote == 1)"'], 'import_lang': 'python -c'}, 'samtools:1.0--1': {'commands': ['samtools --help'], 'import_lang': 'python -c', 'container': 'samtools:1.0--1'}, 'yasm:1.3.0--0': {}}, 'singularity', tmp_dir)
    assert 'samtools:1.0--1' in results['passed']
    assert results['failed'][0]['imports'] == ['pyBigWig']
    assert 'yasm:1.3.0--0' in results['notest']
    shutil.rmtree('/tmp/singtest')

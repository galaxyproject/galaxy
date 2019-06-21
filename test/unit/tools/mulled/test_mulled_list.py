from galaxy.tools.deps.mulled.mulled_list import get_missing_containers, get_missing_envs, get_singularity_containers

# def test_get_quay_containers():
#     lst = get_quay_containers()
#     assert 'samtools:1.0--1' in lst
#     assert 'abricate:0.4--pl5.22.0_0' in lst
#     assert 'samtools' not in lst


def test_get_singularity_containers():
    lst = get_singularity_containers()
    assert 'aragorn:1.2.36--1' in lst
    assert 'znc:latest' not in lst


def test_get_missing_containers():
    from os import remove
    with open('/tmp/blacklist.txt', 'w') as f:
        f.write('a\n\nb\nc\nd')
    containers = get_missing_containers(quay_list=['1', '2', '3', 'a', 'b', 'z'], singularity_list=['3', '4', '5'], blacklist_file='/tmp/blacklist.txt')
    assert containers == ['1', '2', 'z']
    remove('/tmp/blacklist.txt')


def test_get_missing_envs():
    from os import remove
    with open('/tmp/blacklist.txt', 'w') as f:
        f.write('a\n\nb\nc\nd')
    envs = get_missing_envs(quay_list=['1', '2', '3', 'a', 'b--2', 'z--1'], conda_list=['3', '4', '5'], blacklist_file='/tmp/blacklist.txt')
    assert envs == ['1', '2', 'z--1']
    remove('/tmp/blacklist.txt')

from galaxy.jobs import JobDestination


def dyndest_chain_1():
    # Check whether chaining dynamic job destinations work
    return "dyn_dest2"


def dyndest_chain_2(tmp_dir_prefix):
    # Chain to yet a third
    return JobDestination(
        runner="dynamic",
        params={'type': 'python',
                'function': 'dyndest_chain_3',
                'tmp_dir_prefix': '%sand2' % tmp_dir_prefix})


def dyndest_chain_3(tmp_dir_prefix):
    tmp_dir = '$(mktemp %sand3XXXXXXXXXXXX)' % tmp_dir_prefix
    return JobDestination(runner="local",
                          params={'tmp_dir': tmp_dir})

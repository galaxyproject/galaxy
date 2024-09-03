from galaxy.jobs import JobDestination


def dyndest_chain_1():
    # Return an invalid destination as this module's function
    # should never be called
    return "invalid_destination"


def dyndest_chain_2():
    # Return an invalid destination as this module's function
    # should never be called
    return "invalid_destination"


def dyndest_chain_3(tmp_dir_prefix_two):
    tmp_dir = f"$(mktemp -d -p $(pwd) {tmp_dir_prefix_two}and3XXXXXXXXXXXX)"
    return JobDestination(runner="local", params={"tmp_dir": tmp_dir})

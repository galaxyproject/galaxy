from galaxy.jobs import JobDestination


def dyndest_chain_1():
    # Return an invalid destination as this module's function
    # should never be called
    return "invalid_destination"


def dyndest_chain_2(tmp_dir_prefix):
    # Chain to yet a third
    return JobDestination(
        runner="dynamic",
        params={
            "type": "python",
            "function": "dyndest_chain_3",
            "rules_module": "integration.chained_dyndest_rules.module3",
            "tmp_dir_prefix_two": "%sand2" % tmp_dir_prefix,
        },
    )


def dyndest_chain_3():
    # Return an invalid destination as this module's function
    # should never be called
    return "invalid_destination"

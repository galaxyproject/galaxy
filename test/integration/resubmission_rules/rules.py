
DEFAULT_INITIAL_DESTINATION = "fail_first_try"


def initial_destination(resource_params):
    return resource_params.get("initial_destination", None) or DEFAULT_INITIAL_DESTINATION

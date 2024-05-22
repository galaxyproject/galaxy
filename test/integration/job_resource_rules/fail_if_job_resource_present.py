def local_or_exception(resource_params):
    """Build environment that fails if resource_params are passed."""
    if resource_params:
        raise Exception("boo!")
    return "local"

from galaxy.util.resources import resource_string


def get_example(filename) -> str:
    return resource_string("galaxy.files.templates.examples", filename)

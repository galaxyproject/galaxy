import yaml
from gxformat2 import (
    from_galaxy_native,
    ImportOptions,
    python_to_workflow,
)

from galaxy.exceptions import MalformedContents


def convert_to_format2(as_dict, json_wrapper: bool):
    return from_galaxy_native(as_dict, None, json_wrapper=json_wrapper)


def convert_from_format2(as_dict, workflow_directory: str | None):
    # Format 2 Galaxy workflow.
    import_options = ImportOptions()
    import_options.deduplicate_subworkflows = True
    try:
        as_dict = python_to_workflow(
            as_dict, galaxy_interface=None, workflow_directory=workflow_directory, import_options=import_options
        )
    except yaml.scanner.ScannerError as e:
        raise MalformedContents(str(e))
    return as_dict

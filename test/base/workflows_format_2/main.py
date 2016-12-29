"""Module containing :func:`convert_and_import_workflow`."""
import os

import yaml

from .converter import python_to_workflow, yaml_to_workflow
from .interface import BioBlendImporterGalaxyInterface


def convert_and_import_workflow(has_workflow, **kwds):
    """Function is main entry for conversion and import of Format 2 workflows."""
    galaxy_interface = kwds.get("galaxy_interface", None)
    if galaxy_interface is None:
        galaxy_interface = BioBlendImporterGalaxyInterface(**kwds)

    source_type = kwds.get("source_type", None)
    workflow_directory = kwds.get("workflow_directory", None)
    if source_type == "path":
        workflow_path = has_workflow
        if workflow_directory is None:
            workflow_directory = os.path.dirname(has_workflow)
        with open(workflow_path, "r") as f:
            has_workflow = yaml.load(f)

    if workflow_directory is not None:
        workflow_directory = os.path.abspath(workflow_directory)

    if isinstance(has_workflow, dict):
        workflow = python_to_workflow(has_workflow, galaxy_interface, workflow_directory)
    else:
        workflow = yaml_to_workflow(has_workflow, galaxy_interface, workflow_directory)

    publish = kwds.get("publish", False)
    exact_tools = kwds.get("exact_tools", False)
    import_kwds = {}
    if publish:
        import_kwds["publish"] = True
    if exact_tools:
        import_kwds["exact_tools"] = True
    return galaxy_interface.import_workflow(workflow, **import_kwds)


__all__ = (
    'convert_and_import_workflow',
)

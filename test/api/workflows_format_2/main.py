from .interface import BioBlendImporterGalaxyInterface
from .converter import yaml_to_workflow, python_to_workflow


def convert_and_import_workflow(has_workflow, **kwds):
    """
    """
    galaxy_interface = kwds.get("galaxy_interface", None)
    if galaxy_interface is None:
        galaxy_interface = BioBlendImporterGalaxyInterface(**kwds)

    if isinstance(has_workflow, dict):
        workflow = python_to_workflow(has_workflow)
    else:
        workflow = yaml_to_workflow(has_workflow)

    return galaxy_interface.import_workflow(workflow)

__all__ = [
    'convert_and_import_workflow',
]

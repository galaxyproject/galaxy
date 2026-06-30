"""Workflow file loading utilities."""

import json
import logging

log = logging.getLogger(__name__)


def load_workflow(path: str) -> dict:
    """Load a workflow from a .ga or .gxwf.yml file."""
    with open(path) as f:
        if path.endswith((".yml", ".yaml")):
            try:
                from galaxy.util.yaml_util import ordered_load

                return ordered_load(f)
            except ImportError:
                import yaml

                return yaml.safe_load(f)
        else:
            return json.load(f)

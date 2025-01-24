"""Utilities for loading tools and workflows from paths for admin user requests."""

from typing import (
    Any,
    Dict,
    Optional,
)

import yaml

from galaxy import exceptions
from galaxy.util import in_directory


def artifact_class(trans, as_dict: Dict[str, Any], allow_in_directory: Optional[str] = None):
    object_id = as_dict.get("object_id", None)
    if as_dict.get("src", None) == "from_path":
        workflow_path = as_dict.get("path")
        allow = not trans or trans.user_is_admin
        allow = allow or (allow_in_directory and in_directory(workflow_path, allow_in_directory))

        if not allow:
            raise exceptions.AdminRequiredException()

        if not isinstance(workflow_path, str):
            raise exceptions.RequestParameterInvalidException()

        with open(workflow_path) as f:
            as_dict = yaml.safe_load(f)

    artifact_class = as_dict.get("class", None)
    if artifact_class is None and "$graph" in as_dict:
        object_id = object_id or "main"
        graph = as_dict["$graph"]
        target_object = None
        if isinstance(graph, dict):
            target_object = graph.get(object_id)
        else:
            for item in graph:
                found_id = item.get("id")
                if found_id == object_id or found_id == f"#{object_id}":
                    target_object = item

        if target_object and target_object.get("class"):
            artifact_class = target_object["class"]

    return artifact_class, as_dict, object_id


__all__ = ("artifact_class",)

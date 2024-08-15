"""This package is something a placeholder for workflow resource parameters.

This file defines the baked in resource mapper types, and this package contains an
example of a more open, pluggable approach with greater control.
"""

import functools
import logging
import os
import sys
from copy import deepcopy

import yaml

import galaxy.util

log = logging.getLogger(__name__)


def get_resource_mapper_function(app):
    config = app.config
    mapper = getattr(config, "workflow_resource_params_mapper", None)

    if mapper is None:
        return _null_mapper_function
    elif ":" in mapper:
        raw_function = _import_resource_mapping_function(mapper)
        # Bind resource parameters here just to not re-parse over and over.
        workflow_resource_params = _read_defined_parameter_definitions(config)
        return functools.partial(raw_function, workflow_resource_params=workflow_resource_params)
    else:
        workflow_resource_params = _read_defined_parameter_definitions(config)
        with open(mapper) as f:
            mapper_definition = yaml.safe_load(f)

        if "by_group" in mapper_definition:
            by_group = mapper_definition["by_group"]
            return functools.partial(
                _resource_parameters_by_group, by_group=by_group, workflow_resource_params=workflow_resource_params
            )
        else:
            raise Exception("Currently workflow parameter mapper definitions require a by_group definition.")


def _read_defined_parameter_definitions(config):
    params_file = getattr(config, "workflow_resource_params_file", None)
    if not params_file or not os.path.exists(params_file):
        # Just re-use job resource parameters.
        params_file = getattr(config, "job_resource_params_file", None)
    if not params_file or not os.path.exists(params_file):
        params_file = None
    log.debug(f"Loading workflow resource parameter definitions from {params_file}")
    if params_file:
        return galaxy.util.parse_resource_parameters(params_file)
    else:
        return {}


def _resource_parameters_by_group(trans, **kwds):
    user = trans.user
    by_group = kwds["by_group"]
    workflow_resource_params = kwds["workflow_resource_params"]

    params = []
    if validate_by_group_workflow_parameters_mapper(by_group, workflow_resource_params):
        user_permissions = {}
        user_groups = []
        for g in user.groups:
            user_groups.append(g.group.name)
        default_group = by_group.get("default", None)
        for group_name, group_def in by_group.get("groups", {}).items():
            if group_name == default_group or group_name in user_groups:
                for tag in group_def:
                    if isinstance(tag, dict):
                        if tag.get("name") not in user_permissions:
                            user_permissions[tag.get("name")] = {}
                        for option in tag.get("options"):
                            user_permissions[tag.get("name")][option] = {}
                    else:
                        if tag not in user_permissions:
                            user_permissions[tag] = {}

        # user_permissions is now set.
        params = get_workflow_parameter_list(workflow_resource_params, user_permissions)
    return params


# returns an array of parameters that a users set of permissions can access.
def get_workflow_parameter_list(params, user_permissions):
    param_list = []
    for param_elem in params.values():
        attr = deepcopy(param_elem.attrib)
        if attr["name"] in user_permissions:
            # Allow 'select' type parameters to be used
            if attr["type"] == "select":
                option_data = []
                reject_list = []
                for option_elem in param_elem.findall("option"):
                    if option_elem.attrib["value"] in user_permissions[attr["name"]]:
                        option_data.append({"label": option_elem.attrib["label"], "value": option_elem.attrib["value"]})
                    else:
                        reject_list.append(option_elem.attrib["label"])
                attr["data"] = option_data
                attr_help = ""
                if "help" in attr:
                    attr_help = attr["help"]
                if reject_list:
                    attr_help += (
                        "<br/><br/>The following options are available but disabled.<br/>"
                        + str(reject_list)
                        + "<br/>If you believe this is a mistake, please contact your Galaxy admin."
                    )
                attr["help"] = attr_help

            param_list.append(attr)
    return param_list


def validate_by_group_workflow_parameters_mapper(by_group, workflow_resource_params):
    valid = True
    try:
        if "default" not in by_group:
            raise Exception("'workflow_resource_params_mapper' YAML file is malformed, 'default' attribute not found!")
        default_group = by_group["default"]
        if "groups" not in by_group:
            raise Exception("'workflow_resource_params_mapper' YAML file is malformed, 'groups' attribute not found!")
        if default_group not in by_group["groups"]:
            raise Exception(
                "'workflow_resource_params_mapper' YAML file is malformed, default group with title '"
                + default_group
                + "' not found in 'groups'!"
            )
        for group in by_group["groups"]:
            for attrib in by_group["groups"][group]:
                if isinstance(attrib, dict):
                    if "name" not in attrib:
                        raise Exception(
                            "'workflow_resource_params_mapper' YAML file is malformed, "
                            "'name' attribute not found in attribute of group '" + group + "'!"
                        )
                    if attrib["name"] not in workflow_resource_params:
                        raise Exception(
                            "'workflow_resource_params_mapper' YAML file is malformed, group with name '"
                            + attrib["name"]
                            + "' not found in 'workflow_resource_params'!"
                        )
                    if "options" not in attrib:
                        raise Exception(
                            "'workflow_resource_params_mapper' YAML file is malformed, "
                            "'options' attribute not found in attribute of group '" + group + "'!"
                        )

                    valid_options = []
                    for param_option in workflow_resource_params[attrib["name"]]:
                        valid_options.append(param_option.attrib["value"])
                    for option in attrib["options"]:
                        if option not in valid_options:
                            raise Exception(
                                "'workflow_resource_params_mapper' YAML file is malformed, '"
                                + option
                                + "' in 'options' of '"
                                + attrib["name"]
                                + "' not found in attribute of group '"
                                + group
                                + "'!"
                            )
                else:
                    if attrib not in workflow_resource_params:
                        raise Exception(
                            "'workflow_resource_params_mapper' YAML file is malformed, attribute with name "
                            "'" + attrib + "' not found in 'workflow_resource_params'!"
                        )

    except Exception as e:
        log.exception(e)
        valid = False

    return valid


def _import_resource_mapping_function(qualified_function_path):
    full_module_name, function_name = qualified_function_path.split(":", 1)
    try:
        __import__(full_module_name)
    except ImportError:
        raise Exception(f"Failed to find workflow resource mapper module {full_module_name}")

    module = sys.modules[full_module_name]
    if hasattr(module, function_name):
        return getattr(module, function_name)
    else:
        raise Exception(f"Failed to find workflow resource mapper function {full_module_name}.{function_name}")


def _null_mapper_function(*args, **kwds):
    return None

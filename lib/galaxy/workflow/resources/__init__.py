"""This package is something a placeholder for workflow resource parameters.

This file defines the baked in resource mapper types, and this package contains an
example of a more open, pluggable approach with greater control.
"""
import functools
import logging
import os
import sys

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
        with open(mapper, "r") as f:
            mapper_definition = yaml.load(f)

        if "by_group" in mapper_definition:
            by_group = mapper_definition["by_group"]
            return functools.partial(_resource_options_by_group, by_group=by_group, workflow_resource_params=workflow_resource_params)
        else:
            raise Exception("Currently workflow parameter mapper definitions require a by_group definition.")


def _read_defined_parameter_definitions(config):
    params_file = getattr(config, "workflow_resource_params_file", None)
    if not params_file or not os.path.exists(params_file):
        # Just re-use job resource parameters.
        params_file = getattr(config, "job_resource_params_file", None)
    if not params_file or not os.path.exists(params_file):
        params_file = None
    log.debug("Loading workflow resource parameter definitions from %s" % params_file)
    if params_file:
        return galaxy.util.parse_resource_parameters(params_file)
    else:
        return {}


def _resource_options_by_group(self, trans, **kwds):
    user = trans.user
    by_group = kwds["by_group"]
    workflow_resource_params = kwds["workflow_resource_params"]

    user_permissions = {}
    user_groups = []
    for g in user.groups:
        user_groups.append(g.group.name)
    default_group = by_group.get('default', None)
    for group_name, group_def in by_group.get("groups", {}).items():
        if group_name == default_group or group_name in user_groups:
            # TODO: Redo get_workflow_options_user_permissions for YAML definition...
            pass

    # user_permissions is now set.
    params = get_workflow_options_param_list(workflow_resource_params, user_permissions)
    return params


# returns an array of parameters that a users set of permissions can access.
def get_workflow_options_param_list(params, user_permissions):
    param_list = []
    for param_name, param_elem in params.items():
        attr = param_elem.attrib
        if attr['name'] in user_permissions:
            # Allow 'select' type parameters to be used
            if attr['type'] == 'select':
                option_data = []
                reject_list = []
                for option_elem in param_elem.findall("option"):
                    if option_elem.attrib['value'] in user_permissions[attr['name']]:
                        option_data.append({
                            'label': option_elem.attrib['label'],
                            'value': option_elem.attrib['value']
                        })
                    else:
                        reject_list.append(option_elem.attrib['label'])
                attr['data'] = option_data

                attr_help = ""
                if 'help' in attr:
                    attr_help = attr['help']
                if reject_list:
                    attr_help += "<br/><br/>The following options are available but disabled.<br/>" + \
                                 str(reject_list) + \
                                 "<br/>If you believe this is a mistake, please contact your Galaxy admin."
                attr['help'] = attr_help

            param_list.append(attr)
    return param_list


def validate_workflow_options_mapper(resource_param_mapper):
    # TODO: Rework this to consume YAML mapper file, drop all parameter validation I think?

    valid = True
    try:
        resource_definitions = parse_xml(resource_param_file)

        # used to validate that groups that specify options from a select parameter are using valid values
        select_params = {}
        all_params = []

        # Validate <parameters>
        param_definitions_root = resource_definitions.getroot().find("parameters")
        for param_elem in param_definitions_root.findall("param"):
            attr = param_elem.attrib
            if 'name' not in attr:
                raise Exception("'param' Element is malformed! 'name' attribute not found!")
            if 'type' not in attr:
                raise Exception("'param' Element is malformed! 'type' attribute not found!")
            if attr['type'] == 'select':
                select_params[attr['name']] = []
                for option_elem in param_elem.findall("option"):
                    if 'value' not in option_elem.attrib:
                        raise Exception("'option' Element is malformed! 'value' attribute not found!")
                    if 'label' not in option_elem.attrib:
                        raise Exception("'option' Element is malformed! 'label' attribute not found!")
                    select_params[attr['name']].append(option_elem.attrib['value'])
            all_params.append(attr['name'])

        # Validate <groups>
        group_definitions_root = resource_definitions.getroot().find("groups")
        if 'default' not in group_definitions_root.attrib:
            raise Exception("'groups' Element is malformed! No 'default' specified!")
        default_name = group_definitions_root.attrib['default']
        has_default = False
        for group in group_definitions_root.findall("group"):
            if 'name' not in group.attrib:
                raise Exception("'group' Element is malformed! 'name' attribute not found!")
            if group.attrib['name'] == default_name:
                has_default = True
            for child in group.getchildren():
                if child.tag not in all_params:
                    raise Exception("'group' Element is malformed! "
                                    "Child '" + child.tag + "' not found in <parameters>!")
                if child.tag in select_params:
                    for att in child.text.split(","):
                        if att not in select_params[child.tag]:
                            raise Exception("Child '" + child.tag + "' of group '" + group.attrib['name'] +
                                            "' is malformed! '" + att + "' not found as a param option!")
        # make sure default is set correctly
        if has_default is False:
            raise Exception("Defined default '" + default_name + "' not found!")

    except Exception as e:
        log.exception(e)
        valid = False
        pass

    return valid


def _import_resource_mapping_function(self, qualified_function_path):
    full_module_name, function_name = qualified_function_path.split(":", 1)
    try:
        __import__(full_module_name)
    except ImportError:
        raise Exception("Failed to find workflow resource mapper module %s" % (full_module_name))

    module = sys.modules[full_module_name]
    if hasattr(module, function_name):
        return getattr(module, function_name)
    else:
        raise Exception("Failed to find workflow resource mapper function %s.%s" % (full_module_name, function_name))


def _null_mapper_function(*args, **kwds):
    return None

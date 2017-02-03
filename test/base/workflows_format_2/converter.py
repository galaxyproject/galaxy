"""Functionality for converting a Format 2 workflow into a standard Galaxy workflow."""
from __future__ import print_function

import json
import os
import sys
import uuid
from collections import OrderedDict

import yaml


STEP_TYPES = [
    "subworkflow",
    "data_input",
    "data_collection_input",
    "tool",
    "pause",
    "parameter_input",
]

STEP_TYPE_ALIASES = {
    'input': 'data_input',
    'input_collection': 'data_collection_input',
    'parameter': 'parameter_input',
}

RUN_ACTIONS_TO_STEPS = {
    'GalaxyWorkflow': 'run_workflow_to_step',
}


def yaml_to_workflow(has_yaml, galaxy_interface, workflow_directory):
    """Convert a Format 2 workflow into standard Galaxy format from supplied stream."""
    as_python = yaml.load(has_yaml)
    return python_to_workflow(as_python, galaxy_interface, workflow_directory)


def python_to_workflow(as_python, galaxy_interface, workflow_directory):
    """Convert a Format 2 workflow into standard Galaxy format from supplied dictionary."""
    if workflow_directory is None:
        workflow_directory = os.path.abspath(".")

    conversion_context = ConversionContext(
        galaxy_interface,
        workflow_directory,
    )
    return _python_to_workflow(as_python, conversion_context)


def _python_to_workflow(as_python, conversion_context):

    if not isinstance(as_python, dict):
        raise Exception("This is not a not a valid Galaxy workflow definition.")

    if "class" not in as_python:
        raise Exception("This is not a not a valid Galaxy workflow definition, must define a class.")

    if as_python["class"] != "GalaxyWorkflow":
        raise Exception("This is not a not a valid Galaxy workflow definition, 'class' must be 'GalaxyWorkflow'.")

    _ensure_defaults(as_python, {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "annotation": "",
        "name": "Workflow",
        "uuid": str(uuid.uuid4()),
    })

    steps = as_python["steps"]

    # If an inputs section is defined, build steps for each
    # and add to steps array.
    if "inputs" in as_python:
        inputs = as_python["inputs"]
        convert_inputs_to_steps(inputs, steps)

    if isinstance(steps, list):
        steps_as_dict = OrderedDict()
        for i, step in enumerate(steps):
            steps_as_dict[str(i)] = step
            if "id" not in step:
                step["id"] = i

            if "label" in step:
                label = step["label"]
                conversion_context.labels[label] = i

            if "position" not in step:
                # TODO: this really should be optional in Galaxy API.
                step["position"] = {
                    "left": 10 * i,
                    "top": 10 * i
                }

        as_python["steps"] = steps_as_dict
        steps = steps_as_dict

    for step in steps.values():
        step_type = step.get("type", None)
        if "run" in step:
            if step_type is not None:
                raise Exception("Steps specified as run actions cannot specify a type.")
            run_action = step.get("run")
            if "@import" in run_action:
                if len(run_action) > 1:
                    raise Exception("@import must be only key if present.")

                run_action_path = run_action["@import"]
                runnable_path = os.path.join(conversion_context.workflow_directory, run_action_path)
                with open(runnable_path, "r") as f:
                    runnable_description = yaml.load(f)
                    run_action = runnable_description

            run_class = run_action["class"]
            run_to_step_function = eval(RUN_ACTIONS_TO_STEPS[run_class])

            run_to_step_function(conversion_context, step, run_action)
            del step["run"]

    for step in steps.values():
        step_type = step.get("type", "tool")
        step_type = STEP_TYPE_ALIASES.get(step_type, step_type)
        if step_type not in STEP_TYPES:
            raise Exception("Unknown step type encountered %s" % step_type)
        step["type"] = step_type
        eval("transform_%s" % step_type)(conversion_context, step)

    for output in as_python.get("outputs", []):
        assert isinstance(output, dict), "Output definition must be dictionary"
        assert "source" in output, "Output definition must specify source"

        if "label" in output and "id" in output:
            raise Exception("label and id are aliases for outputs, may only define one")
        if "label" not in output and "id" not in output:
            raise Exception("Output must define a label.")

        raw_label = output.pop("label", None)
        raw_id = output.pop("id", None)
        label = raw_label or raw_id

        source = output["source"]
        id, output_name = conversion_context.step_output(source)
        step = steps[str(id)]
        if "workflow_output" not in step:
            step["workflow_outputs"] = []

        step["workflow_outputs"].append({
            "output_name": output_name,
            "label": label,
            "uuid": output.get("uuid", None)
        })

    return as_python


def convert_inputs_to_steps(inputs, steps):
    new_steps = []
    for input_def_raw in inputs:
        input_def = input_def_raw.copy()

        if "label" in input_def and "id" in input_def:
            raise Exception("label and id are aliases for inputs, may only define one")
        if "label" not in input_def and "id" not in input_def:
            raise Exception("Input must define a label.")

        raw_label = input_def.pop("label", None)
        raw_id = input_def.pop("id", None)
        label = raw_label or raw_id

        if not label:
            raise Exception("Input label must not be empty.")

        input_type = input_def.pop("type", "data")
        if input_type in ["File", "data", "data_input"]:
            step_type = "data_input"
        elif input_type in ["collection", "data_collection", "data_collection_input"]:
            step_type = "data_collection_input"
        elif input_type in ["text", "integer", "float", "color", "boolean"]:
            step_type = "parameter_input"
            input_def["parameter_type"] = input_type
        else:
            raise Exception("Input type must be a data file or collection.")

        step_def = input_def
        step_def.update({
            "type": step_type,
            "label": label,
        })
        new_steps.append(step_def)

    for i, new_step in enumerate(new_steps):
        steps.insert(i, new_step)


def run_workflow_to_step(conversion_context, step, run_action):
    subworkflow_conversion_context = conversion_context.get_subworkflow_conversion_context(step)

    step["type"] = "subworkflow"
    step["subworkflow"] = _python_to_workflow(
        run_action,
        subworkflow_conversion_context,
    )


def transform_data_input(context, step):
    transform_input(context, step, default_name="Input dataset")


def transform_data_collection_input(context, step):
    transform_input(context, step, default_name="Input dataset collection")


def transform_parameter_input(context, step):
    transform_input(context, step, default_name="input_parameter")


def transform_input(context, step, default_name):
    default_name = step.get("label", default_name)
    _ensure_defaults(step, {
        "annotation": "",
    })

    _ensure_inputs_connections(step)

    if "inputs" not in step:
        step["inputs"] = [{}]

    step_inputs = step["inputs"][0]
    if "name" in step_inputs:
        name = step_inputs["name"]
    else:
        name = default_name

    _ensure_defaults(step_inputs, {
        "name": name,
        "description": "",
    })
    tool_state = {
        "name": name
    }
    for attrib in ["collection_type", "parameter_type", "optional"]:
        if attrib in step:
            tool_state[attrib] = step[attrib]

    _populate_tool_state(step, tool_state)


def transform_pause(context, step, default_name="Pause for dataset review"):
    default_name = step.get("label", default_name)
    _ensure_defaults(step, {
        "annotation": "",
    })

    _ensure_inputs_connections(step)

    if "inputs" not in step:
        step["inputs"] = [{}]

    step_inputs = step["inputs"][0]
    if "name" in step_inputs:
        name = step_inputs["name"]
    else:
        name = default_name

    _ensure_defaults(step_inputs, {
        "name": name,
    })
    tool_state = {
        "name": name
    }

    connect = _init_connect_dict(step)
    _populate_input_connections(context, step, connect)
    _populate_tool_state(step, tool_state)


def transform_subworkflow(context, step):
    _ensure_defaults(step, {
        "annotation": "",
    })

    _ensure_inputs_connections(step)

    tool_state = {
    }

    connect = _init_connect_dict(step)
    _populate_input_connections(context, step, connect)
    _populate_tool_state(step, tool_state)


def transform_tool(context, step):
    if "tool_id" not in step:
        raise Exception("Tool steps must define a tool_id.")

    _ensure_defaults(step, {
        "annotation": "",
        "name": step['tool_id'],
        "post_job_actions": {},
        "tool_version": None,
    })
    post_job_actions = step["post_job_actions"]

    tool_state = {
        # TODO: Galaxy should not require tool state actually specify a __page__.
        "__page__": 0,
    }

    connect = _init_connect_dict(step)

    def append_link(key, value):
        if key not in connect:
            connect[key] = []
        connect[key].append(value["$link"])

    def replace_links(value, key=""):
        if _is_link(value):
            append_link(key, value)
            # Filled in by the connection, so to force late
            # validation of the field just mark as RuntimeValue.
            # It would be better I guess if this were some other
            # value dedicated to this purpose (e.g. a ficitious
            # {"__class__": "ConnectedValue"}) that could be further
            # validated by Galaxy.
            return {"__class__": "RuntimeValue"}
        if isinstance(value, dict):
            new_values = {}
            for k, v in value.items():
                new_key = _join_prefix(key, k)
                new_values[k] = replace_links(v, new_key)
            return new_values
        elif isinstance(value, list):
            new_values = []
            for i, v in enumerate(value):
                # If we are a repeat we need to modify the key
                # but not if values are actually $links.
                if _is_link(v):
                    append_link(key, v)
                    new_values.append(None)
                else:
                    new_key = "%s_%d" % (key, i)
                    new_values.append(replace_links(v, new_key))
            return new_values
        else:
            return value

    if "state" in step:
        step_state = step["state"]
        step_state = replace_links(step_state)

        for key, value in step_state.items():
            tool_state[key] = json.dumps(value)
        del step["state"]

    # Fill in input connections
    _populate_input_connections(context, step, connect)

    _populate_tool_state(step, tool_state)

    # Handle outputs.
    if "outputs" in step:
        for name, output in step.get("outputs", {}).items():
            if output.get("hide", False):
                action_name = "HideDatasetAction%s" % name
                action = _action(
                    "HideDatasetAction",
                    name,
                )
                post_job_actions[action_name] = action

            if output.get("rename", None):
                new_name = output.get("rename")
                action_name = "RenameDatasetAction%s" % name
                arguments = dict(newname=new_name)
                action = _action(
                    "RenameDatasetAction",
                    name,
                    arguments,
                )
                post_job_actions[action_name] = action

            if output.get("delete_intermediate_datasets", None):
                action_name = "DeleteIntermediatesAction%s" % name
                arguments = dict()
                action = _action(
                    "DeleteIntermediatesAction",
                    name,
                    arguments,
                )
                post_job_actions[action_name] = action

        del step["outputs"]


def run_tool_to_step(conversion_context, step, run_action):
    tool_description = conversion_context.galaxy_interface.import_tool(
        run_action
    )
    step["type"] = "tool"
    step["tool_id"] = tool_description["tool_id"]
    step["tool_version"] = tool_description["tool_version"]
    step["tool_hash"] = tool_description["tool_hash"]


class ConversionContext(object):

    def __init__(self, galaxy_interface, workflow_directory):
        self.labels = {}
        self.subworkflow_conversion_contexts = {}
        self.galaxy_interface = galaxy_interface
        self.workflow_directory = workflow_directory

    def step_id(self, label_or_id):
        if label_or_id in self.labels:
            id = self.labels[label_or_id]
        else:
            id = label_or_id
        return int(id)

    def step_output(self, value):
        value_parts = str(value).split("#")
        if len(value_parts) == 1:
            value_parts.append("output")
        id = self.step_id(value_parts[0])
        return id, value_parts[1]

    def get_subworkflow_conversion_context(self, step):
        step_id = step["id"]
        if step_id not in self.subworkflow_conversion_contexts:
            subworkflow_conversion_context = ConversionContext(
                self.galaxy_interface,
                self.workflow_directory,
            )
            self.subworkflow_conversion_contexts[step_id] = subworkflow_conversion_context
        return self.subworkflow_conversion_contexts[step_id]


def _action(type, name, arguments={}):
    return {
        "action_arguments": arguments,
        "action_type": type,
        "output_name": name,
    }


def _is_link(value):
    return isinstance(value, dict) and "$link" in value


def _join_prefix(prefix, key):
    if prefix:
        new_key = "%s|%s" % (prefix, key)
    else:
        new_key = key
    return new_key


def _init_connect_dict(step):
    if "connect" not in step:
        step["connect"] = {}

    connect = step["connect"]
    del step["connect"]
    return connect


def _populate_input_connections(context, step, connect):
    _ensure_inputs_connections(step)
    input_connections = step["input_connections"]
    is_subworkflow_step = step.get("type") == "subworkflow"

    for key, values in connect.items():
        input_connection_value = []
        if not isinstance(values, list):
            values = [values]
        for value in values:
            if not isinstance(value, dict):
                if key == "$step":
                    value += "#__NO_INPUT_OUTPUT_NAME__"
                id, output_name = context.step_output(value)
                value = {"id": id, "output_name": output_name}
                if is_subworkflow_step:
                    subworkflow_conversion_context = context.get_subworkflow_conversion_context(step)
                    input_subworkflow_step_id = subworkflow_conversion_context.step_id(key)
                    value["input_subworkflow_step_id"] = input_subworkflow_step_id
            input_connection_value.append(value)
        if key == "$step":
            key = "__NO_INPUT_OUTPUT_NAME__"
        input_connections[key] = input_connection_value


def _ensure_inputs_connections(step):
    if "input_connections" not in step:
        step["input_connections"] = {}


def _ensure_defaults(in_dict, defaults):
    for key, value in defaults.items():
        if key not in in_dict:
            in_dict[key] = value


def _populate_tool_state(step, tool_state):
    step["tool_state"] = json.dumps(tool_state)


def main(argv):
    print(json.dumps(yaml_to_workflow(argv[0])))


if __name__ == "__main__":
    main(sys.argv)

__all__ = (
    'yaml_to_workflow',
    'python_to_workflow',
)

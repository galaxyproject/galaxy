"""
Methods to create template for history details recursively.
Used in dataset and history controllers
"""

from galaxy.util import listify
from galaxy.web import url_for


def render_item(trans, entity, children):
    """
    Form HTML template for each item in the history
    """
    template = ''
    entity_name = entity.__class__.__name__
    if entity_name == "HistoryDatasetAssociation":
        template = render_item_hda(trans, entity, children)
    elif entity_name == "Job":
        template = render_item_job(trans, entity, children)
    elif entity_name == "WorkflowInvocation":
        template = render_item_wf(trans, entity, children)
    return template


def render_item_hda(trans, hda, children):
    """
    Render hdas as a id'd stub for js to fill later
    """
    template = ''
    if hda.copied_from_history_dataset_association:
        template = render_hda_copied_from_history(trans, hda, children)
    elif hda.copied_from_library_dataset_dataset_association:
        template = render_hda_copied_from_library(trans, hda, children)
    else:
        template = '<div id="hda-' + trans.security.encode_id(hda.id) + '" class="dataset hda state-' + hda.state + '"></div>'
    return template


def render_hda_copied_from_history(trans, hda, children):
    """
    Wrap an hda in info about the history from where it was copied
    """
    template = ''
    id = trans.security.encode_id(hda.id)
    history_id = trans.security.encode_id(hda.copied_from_history_dataset_association.history_id)
    url = url_for('/histories/view?id=' + history_id)
    template = '<div class="copied-from"><div class="header"><div>'
    template += '<span class="light"> Copied from history dataset: </span>'
    template += '<span class="bold">' + hda.copied_from_history_dataset_association.name + '</span>'
    template += '</div><div class="copied-from-source">'
    template += '<span class="light">History: </span>'
    template += '<span class="bold">'
    template += '<a href="' + url + '">' + hda.copied_from_history_dataset_association.history.name + '</a>'
    template += '</span></div></div>'
    template += '<div id="hda-' + id + '" class="dataset hda state-' + hda.state + '"></div></div>'
    return template


def render_hda_copied_from_library(trans, hda, children):
    """
    Wrap an hda in info about the library from where it was copied
    """
    template = ''
    id = trans.security.encode_id(hda.id)
    folder = hda.copied_from_library_dataset_dataset_association.library_dataset.folder
    folder_id = 'F' + trans.security.encode_id(folder.id)
    url = url_for('/library/list#folders/' + folder_id)
    template = '<div class="copied-from">'
    template += '<div class="header">'
    template += '<div>'
    template += '<span class="light">Copied from library dataset:</span>'
    template += '<span class="bold">' + hda.copied_from_library_dataset_dataset_association.name + '</span>'
    template += '</div>'
    template += '<div class="copied-from-source">'
    template += '<span class="light">Library: </span>'
    template += '<span class="bold">'
    template += '<a href="' + url + '">' + folder.name + '</a></span></div></div>'
    template += '<div id="hda-' + id + '" class="dataset hda state-' + hda.state + '"></div></div>'
    return template


def render_item_job(trans, job, children):
    """
    Render a job and its children (hdas)
    """
    template = ''
    template = '<div class="tool">'
    tool = trans.app.toolbox.get_tool(job.tool_id, tool_version=job.tool_version)
    if tool:
        tool_name = tool.name
        tool_desc = tool.description
    else:
        tool_name = "Unknown tool with id: %s" % job.tool_id
        tool_desc = ''
    params_object = None
    try:
        params_object = job.get_param_values(trans.app, ignore_errors=True)
    except Exception:
        pass
    template += '<div class="header"><div><span class="bold">' + tool_name + '</span>'
    template += '<span class="light"> - ' + tool_desc + '</span></div>'
    if tool and params_object:
        template += '<table class="job-inputs">'
        template += inputs_recursive(trans, tool.inputs, params_object, depth=1)
        template += '</table>'
    else:
        template += '<em>No parameter data available</em>'
    template += '</div>'
    template += '<div class="body">'
    child_template = ''
    for e, c in reversed(children):
        child_template += render_item(trans, e, c)
    template += child_template
    template += '</div></div>'
    return template


def render_item_wf(trans, wf, children):
    """
    Render a workflow and its children (jobs)
    """
    template = '<div class="workflow"><div class="header"><span class="bold">' + wf.workflow.name + '</span>'
    template += '<span class="light">- Workflow</span></div><div class="body">'
    for e, c in reversed(children):
        template += render_item(trans, e, c)
    template += '</div></div>'
    return template


def inputs_recursive_indent(text, depth):
    """
    Add an indentation depending on the depth in a <tr>
    """
    return '<td style="padding-left:' + str((depth - 1) * 10) + 'px">' + text + '</td>'


def inputs_recursive(trans, input_params, param_values, depth=1, upgrade_messages=None):
    """
    Recursive method for tool parameter section
    """
    tool_parameter_template = ''
    if upgrade_messages is None:
        upgrade_messages = {}

    for input_index, input in enumerate(input_params.itervalues()):
        if input.name in param_values:
            if input.type == "repeat":
                for i in range(len(param_values[input.name])):
                    inputs_recursive(trans, input.inputs, param_values[input.name][i], depth=depth + 1)
            elif input.type == "section":
                tool_parameter_template += '<tr>'
                tool_parameter_template += inputs_recursive_indent(text=input.name, depth=depth)
                tool_parameter_template += '<td></td></tr>'
                inputs_recursive(trans, input.inputs, param_values[input.name], depth=depth + 1, upgrade_messages=upgrade_messages.get(input.name))
            elif input.type == "conditional":
                try:
                    current_case = param_values[input.name]['__current_case__']
                    is_valid = True
                except Exception:
                    current_case = None
                    is_valid = False
                if is_valid:
                    tool_parameter_template += '<tr>'
                    tool_parameter_template += inputs_recursive_indent(text=input.test_param.label, depth=depth)
                    tool_parameter_template += '<td>' + input.cases[current_case].value + '</td><td></td></tr>'
                    inputs_recursive(trans, input.cases[current_case].inputs, param_values[input.name], depth=depth + 1, upgrade_messages=upgrade_messages.get(input.name))
                else:
                    tool_parameter_template += '<tr>'
                    tool_parameter_template += inputs_recursive_indent(text=input.name, depth=depth)
                    tool_parameter_template += '<td><em> The previously used value is no longer valid </em></td><td></td></tr>'
            elif input.type == "upload_dataset":
                tool_parameter_template += '<tr>'
                tool_parameter_template += inputs_recursive_indent(text=input.group_title(param_values), depth=depth)
                tool_parameter_template += '<td>' + str(len(param_values[input.name])) + ' uploaded datasets</td><td></td></tr>'
            elif input.type == "data":
                tool_parameter_template += '<tr>'
                tool_parameter_template += inputs_recursive_indent(text=input.label, depth=depth)
                tool_parameter_template += '<td>'
                for i, element in enumerate(listify(param_values[input.name])):
                    if i > 0:
                        tool_parameter_template += ','
                    if element.history_content_type == "dataset":
                        hda = element
                        encoded_id = trans.security.encode_id(hda.id)
                        dataset_info_url = url_for(controller="dataset", action="show_params", dataset_id=encoded_id)
                        tool_parameter_template += '<a target="galaxy_main" data-hda-id="' + encoded_id + '"'
                        tool_parameter_template += 'href="' + dataset_info_url + '">' + str(hda.hid) + ':' + hda.name + '</a>'
                    else:
                        tool_parameter_template += str(element.hid) + ':' + element.name
                    tool_parameter_template += '</td><td></td></tr>'
            elif input.visible:
                label = input.label if (hasattr(input, "label") and input.label) else input.name
                tool_parameter_template += '<tr>'
                tool_parameter_template += inputs_recursive_indent(text=label, depth=depth)
                tool_parameter_template += '<td>' + input.value_to_display_text(param_values[input.name]) + '</td>'
                tool_parameter_template += '<td>' + upgrade_messages.get(input.name, '') + '</td></tr>'
        else:
            tool_parameter_template += '<tr>'
            if input.type == "conditional":
                label = input.test_param.label
            elif input.type == "repeat":
                label = input.label()
            else:
                label = input.label or input.name
                tool_parameter_template += inputs_recursive_indent(text=label, depth=depth)
                tool_parameter_template += '<td><em> not used (parameter was added after this job was run)</em></td><td></td></tr>'
    return tool_parameter_template

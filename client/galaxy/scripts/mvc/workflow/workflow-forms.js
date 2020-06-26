import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import Utils from "utils/utils";
import Form from "mvc/form/form-view";
import ToolFormBase from "mvc/tool/tool-form-base";

/** Default form wrapper for non-tool modules in the workflow editor. */
export class DefaultForm {
    constructor(options) {
        var self = this;
        var node = options.node;
        this.workflow = options.workflow;
        _addLabelAnnotation(this, node);
        this.form = new Form({
            ...options,
            onchange() {
                axios
                    .post(`${getAppRoot()}api/workflows/build_module`, {
                        id: node.id,
                        type: node.type,
                        content_id: node.content_id,
                        inputs: self.form.data.create(),
                    })
                    .then((response) => {
                        const data = response.data;
                        node.update_field_data(data);
                    });
            },
        });
    }
}

/** Tool form wrapper for the workflow editor. */
export class ToolForm {
    constructor(options) {
        const self = this;
        const node = options.node;
        this.workflow = options.workflow;
        this.datatypes = options.datatypes;
        this._customize(node);
        this.form = new ToolFormBase({
            ...node.config_form,
            text_enable: "Set in Advance",
            text_disable: "Set at Runtime",
            narrow: true,
            initial_errors: true,
            cls: "ui-portlet-section",
            postchange(process, form) {
                const Galaxy = getGalaxyInstance();
                const options = form.model.attributes;
                const current_state = {
                    tool_id: options.id,
                    tool_version: options.version,
                    type: "tool",
                    inputs: Object.assign({}, form.data.create()),
                };
                Galaxy.emit.debug("tool-form-workflow::postchange()", "Sending current state.", current_state);
                axios
                    .post(`${getAppRoot()}api/workflows/build_module`, current_state)
                    .then((response) => {
                        const data = response.data;
                        self._customize(data);
                        self.form.model.set(data.config_form);
                        self.form.update(data.config_form);
                        self.form.errors(data.config_form);
                        // This hasn't modified the workflow, just returned
                        // module information for the tool to update the workflow
                        // state stored on the client with. User needs to save
                        // for this to take effect.
                        node.update_field_data(data);
                        Galaxy.emit.debug("tool-form-workflow::postchange()", "Received new model.", data);
                        process.resolve();
                    })
                    .catch((response) => {
                        Galaxy.emit.debug("tool-form-workflow::postchange()", "Refresh request failed.", response);
                        process.reject();
                    });
            },
        });
    }
    _customize(node) {
        const inputs = node.config_form.inputs;
        Utils.deepeach(inputs, (input) => {
            if (input.type) {
                if (["data", "data_collection"].indexOf(input.type) != -1) {
                    input.type = "hidden";
                    input.info = `Data input '${input.name}' (${Utils.textify(input.extensions)})`;
                    input.value = { __class__: "RuntimeValue" };
                } else if (!input.fixed) {
                    input.connectable = true;
                    input.collapsible_value = {
                        __class__: "RuntimeValue",
                    };
                    input.is_workflow =
                        (input.options && input.options.length === 0) || ["integer", "float"].indexOf(input.type) != -1;
                }
            }
        });
        Utils.deepeach(inputs, (input) => {
            if (input.type === "conditional") {
                input.connectable = false;
                input.test_param.collapsible_value = undefined;
            }
        });
        _addSections(this, node);
        _addLabelAnnotation(this, node);
    }
}

/** Augments the module form definition by adding label and annotation fields */
function _addLabelAnnotation(self, node) {
    var workflow = self.workflow;
    const inputs = node.config_form.inputs;
    inputs.unshift({
        type: "text",
        name: "__annotation",
        label: "Annotation",
        fixed: true,
        value: node.annotation,
        area: true,
        help: "Add an annotation or notes to this step. Annotations are available when a workflow is viewed.",
    });
    inputs.unshift({
        type: "text",
        name: "__label",
        label: "Label",
        value: node.label,
        help: _l("Add a step label."),
        fixed: true,
        onchange: function (new_label) {
            var duplicate = false;
            for (var i in workflow.nodes) {
                var n = workflow.nodes[i];
                if (n.label && n.label == new_label && n.id != node.id) {
                    duplicate = true;
                    break;
                }
            }
            var input_id = self.form.data.match("__label");
            var input_element = self.form.element_list[input_id];
            input_element.model.set(
                "error_text",
                duplicate && "Duplicate label. Please fix this before saving the workflow."
            );
            self.form.trigger("change");
        },
    });
}

/** Visit input nodes and enrich by name/value pairs from server data */
function _visit(head, head_list, output_id, node) {
    var post_job_actions = node.post_job_actions;
    head_list = head_list || [];
    head_list.push(head);
    for (var i in head.inputs) {
        var input = head.inputs[i];
        var action = input.action;
        if (action) {
            input.name = `pja__${output_id}__${input.action}`;
            if (input.pja_arg) {
                input.name += `__${input.pja_arg}`;
            }
            if (input.payload) {
                for (var p_id in input.payload) {
                    input.payload[`${input.name}__${p_id}`] = input.payload[p_id];
                    delete input.payload[p_id];
                }
            }
            var d = post_job_actions[input.action + output_id];
            if (d) {
                for (var j in head_list) {
                    head_list[j].expanded = true;
                }
                if (input.pja_arg) {
                    input.value = (d.action_arguments && d.action_arguments[input.pja_arg]) || input.value;
                } else {
                    input.value = "true";
                }
            }
        }
        if (input.inputs) {
            _visit(input, head_list.slice(0), output_id, node);
        }
    }
}

function _makeRenameHelp(name_labels) {
    let help_section = `This action will rename the output dataset. Click <a href="https://galaxyproject.org/learn/advanced-workflow/variables/">here</a> for more information. Valid input variables are:`;
    const li = `
        <ul>
            ${name_labels
                .map(
                    (name_label) => `<li><strong>${name_label.name.replace(/\|/g, ".")}</strong>
                                                         ${name_label.label ? `(${name_label.label})` : ""}
                                             </li>`
                )
                .join("")}
        </ul>
    `;
    help_section += li;
    return help_section;
}

/** Builds sub section with step actions/annotation */
function _makeSection(self, output_id, label, node) {
    var extensions = [];
    var name_label_map = [];
    var datatypes = self.datatypes;
    var workflow = self.workflow;
    for (const key in datatypes) {
        extensions.push({ 0: datatypes[key], 1: datatypes[key] });
    }
    for (const key in node.input_terminals) {
        name_label_map.push({ name: node.input_terminals[key].name, label: node.input_terminals[key].label });
    }
    var rename_help = _makeRenameHelp(name_label_map);
    extensions.sort((a, b) => (a.label > b.label ? 1 : a.label < b.label ? -1 : 0));
    extensions.unshift({
        0: "Sequences",
        1: "Sequences",
    });
    extensions.unshift({
        0: "Roadmaps",
        1: "Roadmaps",
    });
    extensions.unshift({
        0: "Leave unchanged",
        1: "__empty__",
    });
    var output;
    var input_config = {
        title: `Configure Output: '${label}'`,
        type: "section",
        flat: true,
        inputs: [
            {
                label: "Label",
                type: "text",
                value: ((output = node.getWorkflowOutput(output_id)) && output.label) || "",
                help: "This will provide a short name to describe the output - this must be unique across workflows.",
                onchange: function (new_value) {
                    workflow.attemptUpdateOutputLabel(node, output_id, new_value);
                },
            },
            {
                action: "RenameDatasetAction",
                pja_arg: "newname",
                label: "Rename dataset",
                type: "text",
                value: "",
                ignore: "",
                help: rename_help,
            },
            {
                action: "ChangeDatatypeAction",
                pja_arg: "newtype",
                label: "Change datatype",
                type: "select",
                ignore: "__empty__",
                value: "__empty__",
                options: extensions,
                help: "This action will change the datatype of the output to the indicated datatype.",
                onchange: function (new_value) {
                    if (new_value === "__empty__") {
                        new_value = null;
                    }
                    workflow.updateDatatype(node, output_id, new_value);
                },
            },
            {
                action: "TagDatasetAction",
                pja_arg: "tags",
                label: "Add Tags",
                type: "text",
                value: "",
                ignore: "",
                help: "This action will set tags for the dataset.",
            },
            {
                action: "RemoveTagDatasetAction",
                pja_arg: "tags",
                label: "Remove Tags",
                type: "text",
                value: "",
                ignore: "",
                help: "This action will remove tags for the dataset.",
            },
            {
                title: _l("Assign columns"),
                type: "section",
                flat: true,
                inputs: [
                    {
                        action: "ColumnSetAction",
                        pja_arg: "chromCol",
                        label: "Chrom column",
                        type: "integer",
                        value: "",
                        ignore: "",
                    },
                    {
                        action: "ColumnSetAction",
                        pja_arg: "startCol",
                        label: "Start column",
                        type: "integer",
                        value: "",
                        ignore: "",
                    },
                    {
                        action: "ColumnSetAction",
                        pja_arg: "endCol",
                        label: "End column",
                        type: "integer",
                        value: "",
                        ignore: "",
                    },
                    {
                        action: "ColumnSetAction",
                        pja_arg: "strandCol",
                        label: "Strand column",
                        type: "integer",
                        value: "",
                        ignore: "",
                    },
                    {
                        action: "ColumnSetAction",
                        pja_arg: "nameCol",
                        label: "Name column",
                        type: "integer",
                        value: "",
                        ignore: "",
                    },
                ],
                help: "This action will set column assignments in the output dataset. Blank fields are ignored.",
            },
        ],
    };
    _visit(input_config, [], output_id, node);
    return input_config;
}

/** Builds all sub sections */
function _addSections(self, node) {
    var inputs = node.config_form.inputs;
    var post_job_actions = node.post_job_actions;
    var output_id = node.output_terminals && Object.keys(node.output_terminals)[0];
    if (output_id) {
        inputs.push({
            name: `pja__${output_id}__EmailAction`,
            label: "Email notification",
            type: "boolean",
            value: String(Boolean(post_job_actions[`EmailAction${output_id}`])),
            ignore: "false",
            help: _l("An email notification will be sent when the job has completed."),
            payload: {
                host: window.location.host,
            },
        });
        inputs.push({
            name: `pja__${output_id}__DeleteIntermediatesAction`,
            label: "Output cleanup",
            type: "boolean",
            value: String(Boolean(post_job_actions[`DeleteIntermediatesAction${output_id}`])),
            ignore: "false",
            help:
                "Upon completion of this step, delete non-starred outputs from completed workflow steps if they are no longer required as inputs.",
        });
        for (const output_id in node.output_terminals) {
            const label = node.output_terminals[output_id].label || output_id;
            inputs.push(_makeSection(self, output_id, label, node));
        }
    }
}

import _l from "utils/localization";

/** Visit input nodes and enrich by name/value pairs from server data */
function _visit(head, head_list, output, node) {
    const postJobActions = node.postJobActions;
    head_list = head_list || [];
    head_list.push(head);
    for (const i in head.inputs) {
        const input = head.inputs[i];
        const action = input.action;
        if (action) {
            input.name = `pja__${output.name}__${input.action}`;
            if (input.pja_arg) {
                input.name += `__${input.pja_arg}`;
            }
            if (input.payload) {
                for (const p_id in input.payload) {
                    input.payload[`${input.name}__${p_id}`] = input.payload[p_id];
                    delete input.payload[p_id];
                }
            }
            const d = postJobActions[input.action + output.name];
            if (d) {
                for (const j in head_list) {
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
            _visit(input, head_list.slice(0), output, node);
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
function _makeSection(node, output, datatypes, onOutputLabel, onOutputDatatype) {
    const extensions = [];
    const name_label_map = [];
    for (const key in datatypes) {
        extensions.push({ 0: datatypes[key], 1: datatypes[key] });
    }
    for (const input of node.inputs) {
        name_label_map.push({ name: input.name, label: input.label });
    }
    const renameHelp = _makeRenameHelp(name_label_map);
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
    const activeOutput = node.activeOutputs.get(output.name);
    const inputTitle = output.label || output.name;
    const inputConfig = {
        skipOnClone: true,
        title: `Configure Output: '${inputTitle}'`,
        type: "section",
        flat: true,
        inputs: [
            {
                label: "Label",
                name: `__label__${output.name}`,
                type: "text",
                value: activeOutput && activeOutput.label,
                help: "This will provide a short name to describe the output - this must be unique across workflows.",
                fixed: true,
                onchange: (newLabel) => {
                    onOutputLabel(node, output.name, newLabel);
                },
            },
            {
                action: "RenameDatasetAction",
                pja_arg: "newname",
                label: "Rename dataset",
                type: "text",
                value: "",
                ignore: "",
                help: renameHelp,
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
                onchange: function (newDatatype) {
                    onOutputDatatype(node, output.name, newDatatype);
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
    _visit(inputConfig, [], output, node);
    return inputConfig;
}

/** Builds all sub sections */
export default function makeSection(node, datatypes, onOutputLabel, onOutputDatatype) {
    const inputs = [];
    const postJobActions = node.postJobActions;
    const outputFirst = node.outputs.length > 0 && node.outputs[0];
    if (outputFirst) {
        inputs.push({
            name: `pja__${outputFirst.name}__EmailAction`,
            label: "Email notification",
            type: "boolean",
            value: String(Boolean(postJobActions[`EmailAction${outputFirst.name}`])),
            ignore: "false",
            help: _l("An email notification will be sent when the job has completed."),
            payload: {
                host: window.location.host,
            },
            skipOnClone: true,
        });
        inputs.push({
            name: `pja__${outputFirst.name}__DeleteIntermediatesAction`,
            label: "Output cleanup",
            type: "boolean",
            value: String(Boolean(postJobActions[`DeleteIntermediatesAction${outputFirst.name}`])),
            ignore: "false",
            help:
                "Upon completion of this step, delete non-starred outputs from completed workflow steps if they are no longer required as inputs.",
            skipOnClone: true,
        });
        for (const output of node.outputs) {
            inputs.push(_makeSection(node, output, datatypes, onOutputLabel, onOutputDatatype));
        }
    }
    return inputs;
}

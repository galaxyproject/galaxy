import _ from "underscore";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import _l from "utils/localization";
import Utils from "utils/utils";
import { DefaultForm, ToolForm } from "./forms";
import { loadWorkflow } from "./services";
import { toSimple } from "./model";
import { hide_modal, show_message, show_modal } from "layout/modal";

export function copyIntoWorkflow(workflow, id = null, stepCount = null) {
    const _copy_into_workflow_ajax = () => {
        // Load workflow definition
        show_message("Importing workflow", "progress");
        loadWorkflow(workflow, id, null, true).then((data) => {
            // Determine if any parameters were 'upgraded' and provide message
            var upgrade_message = "";
            $.each(data.upgrade_messages, (k, v) => {
                upgrade_message += `<li>Step ${parseInt(k, 10) + 1}: ${workflow.steps[k].name}<ul>`;
                $.each(v, (i, vv) => {
                    upgrade_message += `<li>${vv}</li>`;
                });
                upgrade_message += "</ul></li>";
            });
            if (upgrade_message) {
                show_modal(
                    "Subworkflow embedded with changes",
                    `Problems were encountered loading this workflow (possibly a result of tool upgrades). Please review the following parameters and then save.<ul>${upgrade_message}</ul>`,
                    { Continue: hide_modal }
                );
            } else {
                hide_modal();
            }
        });
    };
    if (stepCount < 2) {
        _copy_into_workflow_ajax();
    } else {
        // don't ruin the workflow by adding 50 steps unprompted.
        show_modal(_l("Warning"), `This will copy ${stepCount} new steps into your workflow.`, {
            Cancel: hide_modal,
            Copy: _copy_into_workflow_ajax,
        });
    }
}

export function showWarnings(data) {
    const body = $("<div/>").text(data.message);
    if (data.errors) {
        body.addClass("warningmark");
        var errlist = $("<ul/>");
        $.each(data.errors, (i, v) => {
            $("<li/>").text(v).appendTo(errlist);
        });
        body.append(errlist);
    } else {
        body.addClass("donemark");
    }
    if (data.errors) {
        show_modal("Saving workflow", body, {
            Ok: hide_modal,
        });
    } else {
        hide_modal();
    }
}

export function showAttributes() {
    $(".right-content").hide();
    $("#edit-attributes").show();
}

export function showLint() {
    $(".right-content").hide();
    $("#lint-panel").show();
}

export function showForm(workflow, node, datatypes) {
    if (node && node.config_form && Object.keys(node.config_form).length > 0) {
        const cls = "right-content";
        var id = `${cls}-${node.id}`;
        var $container = $(`#${cls}`);
        if ($container.find(`#${id}`).length === 0) {
            var $el = $(`<div id="${id}" class="${cls}"/>`);
            const options = {
                node,
                workflow,
                datatypes,
            };
            let formWrapper = null;
            if (node.type == "tool") {
                formWrapper = new ToolForm(options);
            } else {
                formWrapper = new DefaultForm(options);
            }
            $el.append(formWrapper.form.$el);
            $container.append($el);
        }
        $(`.${cls}`).hide();
        $container.find(`#${id}`).show();
        $container.show();
        $container.scrollTop();
    }
}

export function showUpgradeMessage(data) {
    // Determine if any parameters were 'upgraded' and provide message
    var upgrade_message = "";
    let hasToolUpgrade = false;
    _.each(data.steps, (step, step_id) => {
        var details = "";
        if (step.errors) {
            details += `<li>${step.errors}</li>`;
        }
        _.each(data.upgrade_messages[step_id], (m) => {
            hasToolUpgrade = true;
            details += `<li>${m}</li>`;
        });
        if (details) {
            upgrade_message += `<li>Step ${parseInt(step_id, 10) + 1}: ${step.name}<ul>${details}</ul></li>`;
        }
    });
    if (upgrade_message) {
        show_modal(
            "Issues loading this workflow",
            `Please review the following issues, possibly resulting from tool upgrades or changes.<p><ul>${upgrade_message}</ul></p>`,
            { Continue: hide_modal }
        );
    } else {
        hide_modal();
    }
    return hasToolUpgrade;
}

class LegacyParameterReference {
    constructor(parameter, node) {
        //this.node = node;
        parameter.references.push(this);
        this.nodeId = node.id;
    }
}

class ToolInputLegacyParameterReference extends LegacyParameterReference {
    constructor(parameter, node, tooInput) {
        super(parameter, node);
        this.toolInput = tooInput;
    }
}

class PjaLegacyParameterReference extends LegacyParameterReference {
    constructor(parameter, node, pja) {
        super(parameter, node);
        this.pja = pja;
    }
}

class LegacyParameter {
    constructor(name) {
        this.name = name;
        this.references = [];
    }

    canExtract() {
        // Backend will indicate errors but would be a bit better to pre-check for them
        // in a future iteration.
        // return false if mixed input types or if say integers are used in PJA?
        return true;
    }
}

export class LegacyParameters {
    constructor() {
        this.parameters = [];
    }

    getParameter(name) {
        for (const parameter of this.parameters) {
            if (parameter.name == name) {
                return parameter;
            }
        }
        const legacyParameter = new LegacyParameter(name);
        this.parameters.push(legacyParameter);
        return legacyParameter;
    }

    getParameterFromMatch(match) {
        return this.getParameter(match.substring(2, match.length - 1));
    }
}

export function getLegacyWorkflowParameters(nodes) {
    const legacyParameters = new LegacyParameters();
    const parameter_re = /\$\{.+?\}/g;
    Object.entries(nodes).forEach(([k, node]) => {
        if (node.config_form && node.config_form.inputs) {
            Utils.deepeach(node.config_form.inputs, (d) => {
                if (typeof d.value == "string") {
                    var form_matches = d.value.match(parameter_re);
                    if (form_matches) {
                        for (const match of form_matches) {
                            const legacyParameter = legacyParameters.getParameterFromMatch(match);
                            new ToolInputLegacyParameterReference(legacyParameter, node, d);
                        }
                    }
                }
            });
        }
        if (node.postJobActions) {
            Object.values(node.postJobActions).forEach((pja) => {
                if (pja.action_arguments) {
                    Object.values(pja.action_arguments).forEach((action_argument) => {
                        if (typeof action_argument === "string") {
                            const arg_matches = action_argument.match(parameter_re);
                            if (arg_matches) {
                                for (const match of arg_matches) {
                                    const legacyParameter = legacyParameters.getParameterFromMatch(match);
                                    new PjaLegacyParameterReference(legacyParameter, node, pja);
                                }
                            }
                        }
                    });
                }
            });
        }
    });
    return legacyParameters;
}

export function getDisconnectedInputs(nodes) {
    const inputs = [];
    Object.entries(nodes).forEach(([k, node]) => {
        Object.entries(node.inputTerminals).forEach(([inputName, inputTerminal]) => {
            if (inputTerminal.connectors && inputTerminal.connectors.length > 0) {
                return;
            }
            if (inputTerminal.optional) {
                return;
            }
            const input = {
                inputName: inputName,
                stepId: node.id,
                stepLabel: node.title, // label but falls back to tool title...
                stepIconClass: node.iconClass,
                inputLabel: inputTerminal.attributes.input.label,
                canExtract: !inputTerminal.multiple,
            };
            inputs.push(input);
        });
    });
    return inputs;
}

export function getInputsMissingMetadata(nodes) {
    const inputs = [];
    Object.entries(nodes).forEach(([k, node]) => {
        if (!node.isInput) {
            return;
        }
        const annotation = node.annotation;
        const label = node.label;
        const missingLabel = !label;
        const missingAnnotation = !annotation;

        if (missingLabel || missingAnnotation) {
            const input = {
                stepLabel: node.title,
                stepIconClass: node.iconClass,
                missingAnnotation: !annotation,
                missingLabel: !label,
            };
            inputs.push(input);
        }
    });
    return inputs;
}

export function getWorkflowOutputs(nodes) {
    const outputs = [];
    Object.entries(nodes).forEach(([k, node]) => {
        if (node.isInput) {
            // For now skip these... maybe should push this logic into linting though
            // since it is fine to have outputs on inputs.
            return;
        }
        const activeOutputs = node.activeOutputs;
        for (const outputDef of activeOutputs.getAll()) {
            const output = {
                outputName: outputDef.output_name,
                outputLabel: outputDef.label,
                stepId: node.id,
                stepLabel: node.title, // label but falls back to tool title...
                stepIconClass: node.iconClass,
            };
            outputs.push(output);
        }
    });
    return outputs;
}

export function saveAs(workflow) {
    var body = $(
        '<form><label style="display:inline-block; width: 100%;">Save as name: </label><input type="text" id="workflow_rename" style="width: 80%;" autofocus/>' +
            '<br><label style="display:inline-block; width: 100%;">Annotation: </label><input type="text" id="wf_annotation" style="width: 80%;" /></form>'
    );
    show_modal("Save As a New Workflow", body, {
        OK: function () {
            var rename_name =
                $("#workflow_rename").val().length > 0 ? $("#workflow_rename").val() : `SavedAs_${workflow.name}`;
            var rename_annotation = $("#wf_annotation").val().length > 0 ? $("#wf_annotation").val() : "";
            $.ajax({
                url: `${getAppRoot()}workflow/save_workflow_as`,
                type: "POST",
                data: {
                    workflow_name: rename_name,
                    workflow_annotation: rename_annotation,
                    from_tool_form: true,
                    workflow_data: () => {
                        return JSON.stringify(toSimple(workflow));
                    },
                },
            })
                .done((id) => {
                    window.onbeforeunload = undefined;
                    window.location = `${getAppRoot()}workflow/editor?id=${id}`;
                    hide_modal();
                })
                .fail((err) => {
                    console.debug(err);
                    hide_modal();
                    alert("Saving this workflow failed. Please contact this site's administrator.");
                });
        },
        Cancel: hide_modal,
    });
}

export function getCompatibleRecommendations(predChild, outputDatatypes, datatypesMapper) {
    const cTools = [];
    const toolMap = new Map();
    for (const nameObj of predChild.entries()) {
        const inputDatatypes = nameObj[1].i_extensions;
        for (const outT of outputDatatypes.entries()) {
            for (const inTool of inputDatatypes.entries()) {
                if (
                    datatypesMapper.isSubType(outT[1], inTool[1]) ||
                    outT[1] === "input" ||
                    outT[1] === "_sniff_" ||
                    outT[1] === "input_collection"
                ) {
                    const toolId = nameObj[1].tool_id;
                    if (!toolMap.has(toolId)) {
                        toolMap.set(toolId, true);
                        cTools.push({
                            id: toolId,
                            name: nameObj[1].name,
                        });
                        break;
                    }
                }
            }
        }
    }
    return cTools;
}

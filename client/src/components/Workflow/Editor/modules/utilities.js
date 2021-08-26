import _ from "underscore";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import _l from "utils/localization";
import { loadWorkflow } from "./services";
import { toSimple } from "./model";
import { show_modal } from "layout/modal";
import WorkflowIcons from "components/Workflow/icons";

export function copyIntoWorkflow(workflow, id = null, stepCount = null) {
    const _copy_into_workflow_ajax = () => {
        // Load workflow definition
        workflow.onWorkflowMessage("Importing workflow", "progress");
        loadWorkflow(workflow, id, null, true).then((data) => {
            // Determine if any parameters were 'upgraded' and provide message
            const insertedStateMessages = getStateUpgradeMessages(data);
            workflow.onInsertedStateMessages(insertedStateMessages);
        });
    };
    if (stepCount < 2) {
        _copy_into_workflow_ajax();
    } else {
        // don't ruin the workflow by adding 50 steps unprompted.
        show_modal(_l("Warning"), `This will copy ${stepCount} new steps into your workflow.`, {
            Cancel: () => {
                workflow.hideModal();
            },
            Copy: _copy_into_workflow_ajax,
        });
    }
}

export function getStateUpgradeMessages(data) {
    // Determine if any parameters were 'upgraded' and provide message
    const messages = [];
    _.each(data.steps, (step, step_id) => {
        const details = [];
        if (step.errors) {
            details.push(step.errors);
        }
        _.each(data.upgrade_messages[step_id], (m) => {
            details.push(m);
        });
        if (details.length) {
            const iconType = WorkflowIcons[step.type];
            const message = {
                stepIndex: step_id,
                name: step.name,
                details: details,
                iconType: iconType,
                label: step.label,
            };
            messages.push(message);
        }
    });
    return messages;
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
                    workflow.onNavigate(`${getAppRoot()}workflow/editor?id=${id}`, true);
                })
                .fail((err) => {
                    console.debug(err);
                    workflow.onWorkflowError(
                        "Saving this workflow failed. Please contact this site's administrator.",
                        err
                    );
                });
        },
        Cancel: () => {
            workflow.hideModal();
        },
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

export function checkLabels(nodeId, newLabel, nodes) {
    let duplicate = false;
    for (const i in nodes) {
        const n = nodes[i];
        if (n.label && n.label == newLabel && n.id != nodeId) {
            duplicate = true;
            break;
        }
    }
    if (duplicate) {
        return "Duplicate label. Please fix this before saving the workflow.";
    } else {
        return "";
    }
}

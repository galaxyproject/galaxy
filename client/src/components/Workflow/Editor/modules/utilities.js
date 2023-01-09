import _ from "underscore";
import WorkflowIcons from "components/Workflow/icons";

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

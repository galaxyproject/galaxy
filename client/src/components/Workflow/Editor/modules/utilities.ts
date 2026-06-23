import WorkflowIcons from "@/components/Workflow/icons";

export interface UpgradeMessage {
    stepIndex: string;
    name: string;
    details: any[];
    iconType: string;
    label: string;
}

export function getStateUpgradeMessages(data: {
    steps: {
        [step_id: string]: {
            name: string;
            type: string;
            label: string;
            errors?: string;
        };
    };
    upgrade_messages: { [step_id: string]: any };
}): UpgradeMessage[] {
    const messages: UpgradeMessage[] = [];
    for (const [step_id, step] of Object.entries(data.steps)) {
        const details = [];
        if (step.errors) {
            details.push(step.errors);
        }
        for (const m of Object.values(data.upgrade_messages[step_id] || {})) {
            details.push(m);
        }
        if (details.length) {
            const iconType = WorkflowIcons[step.type as keyof typeof WorkflowIcons];
            const message: UpgradeMessage = {
                stepIndex: step_id,
                name: step.name,
                details: details,
                iconType: iconType,
                label: step.label,
            };
            messages.push(message);
        }
    }
    return messages;
}

export function getCompatibleRecommendations(predChild: any, outputDatatypes: any, datatypesMapper: any) {
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

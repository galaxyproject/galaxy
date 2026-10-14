import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import WorkflowIcons from "@/components/Workflow/icons";

export interface UpgradeMessage {
    stepIndex: string;
    name: string;
    details: string[];
    iconType: string;
    label: string;
}

// Subworkflow steps nest their inner steps' messages ({"Step 2": {"inttest": "..."}}),
// and the messages themselves are already self-describing, so only the leaves are shown.
function flattenUpgradeMessages(messages: unknown): string[] {
    if (messages === null || messages === undefined) {
        return [];
    }
    if (typeof messages === "object") {
        return Object.values(messages).flatMap(flattenUpgradeMessages);
    }
    return [String(messages)];
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
        const details: string[] = [];
        if (step.errors) {
            details.push(step.errors);
        }
        details.push(...flattenUpgradeMessages(data.upgrade_messages[step_id]));
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

export interface PredictedToolChild {
    name: string;
    tool_id: string;
    tool_score?: number;
    i_extensions?: string[];
}

export interface CompatibleRecommendation {
    id: string;
    name: string;
}

export function getCompatibleRecommendations(
    predChild: PredictedToolChild[],
    outputDatatypes: string[],
    datatypesMapper: DatatypesMapperModel,
): CompatibleRecommendation[] {
    const cTools: CompatibleRecommendation[] = [];
    const toolMap = new Map<string, boolean>();
    for (const child of predChild) {
        const inputDatatypes = child.i_extensions ?? [];
        for (const outT of outputDatatypes) {
            for (const inTool of inputDatatypes) {
                if (
                    datatypesMapper.isSubType(outT, inTool) ||
                    outT === "input" ||
                    outT === "_sniff_" ||
                    outT === "input_collection"
                ) {
                    const toolId = child.tool_id;
                    if (!toolMap.has(toolId)) {
                        toolMap.set(toolId, true);
                        cTools.push({
                            id: toolId,
                            name: child.name,
                        });
                        break;
                    }
                }
            }
        }
    }
    return cTools;
}

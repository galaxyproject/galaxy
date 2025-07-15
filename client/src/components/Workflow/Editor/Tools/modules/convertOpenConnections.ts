import { getModule } from "@/components/Workflow/Editor/modules/services";
import { onAllInputs } from "@/components/Workflow/Editor/Tools/modules/onAllInputs";
import type { WorkflowSearchStore } from "@/stores/workflowSearchStore";
import {
    type CollectionOutput,
    type ConnectionOutputLink,
    createNewStep,
    type ParameterOutput,
    type Step,
} from "@/stores/workflowStepStore";
import { assertDefined, ensureDefined } from "@/utils/assertions";
import { match } from "@/utils/utils";

/** Find input connections which are unconnected */
function getOpenInputConnections(selectedKeys: number[], allSteps: Record<number, Step>) {
    const selection = selectedKeys.map((key) => ensureDefined(allSteps[key]));
    const selectedKeysSet = new Set(selectedKeys);
    const openInputConnections: ConnectionOutputLink[] = [];

    selection.forEach((step) => {
        onAllInputs(step, (connection) => {
            if (!selectedKeysSet.has(connection.id)) {
                openInputConnections.push(connection);
            }
        });
    });

    return openInputConnections;
}

/** Find output connections which are unconnected */
function getOpenOutputConnections(selectedKeys: number[], allSteps: Record<number, Step>) {
    const selectedKeysSet = new Set(selectedKeys);
    const notSelected = Object.values(allSteps).filter((step) => !selectedKeysSet.has(step.id));
    const openOutputConnections: { connection: ConnectionOutputLink; name: string; nodeId: number }[] = [];

    notSelected.forEach((step) => {
        onAllInputs(step, (connection, name) => {
            if (selectedKeysSet.has(connection.id)) {
                const connectedNode = ensureDefined(allSteps[connection.id]);

                // don't count open input node outputs as open connections
                if (!["data_input", "data_collection_input", "parameter_input"].includes(connectedNode.type)) {
                    openOutputConnections.push({ connection, name, nodeId: step.id });
                }
            }
        });
    });

    return openOutputConnections;
}

function prettifyInputName(
    type: "data_input" | "data_collection_input" | "parameter_input",
    subType: undefined | "text" | "integer" | "float" | "boolean" | "color" | "directory_uri",
    index: number,
    allStepLabels: Set<string>
) {
    const getName = (count: number) => {
        if (type === "data_input") {
            return `Input Dataset ${count}`;
        } else if (type === "data_collection_input") {
            return `Input Dataset Collection ${count}`;
        } else if (type === "parameter_input") {
            assertDefined(subType);

            return match(subType, {
                boolean: () => `Boolean Input ${count}`,
                color: () => `Color Inputs ${count}`,
                directory_uri: () => `Directory Input ${count}`,
                float: () => `Float Input ${count}`,
                integer: () => `Integer Inputs ${count}`,
                text: () => `Text Inputs ${count}`,
            });
        } else {
            return `Input ${count}`;
        }
    };

    let currentCount = index + 1;
    let currentName = getName(currentCount);

    // increment count to avoid duplicate labels
    while (allStepLabels.has(currentName)) {
        currentCount += 1;
        currentName = getName(currentCount);
    }

    return currentName;
}

// small hardcoded position correction estimate to improve look of input nodes
const OUTPUT_TO_NODE_POSITION_CORRECTION = { top: -73, left: -3 };

/** converts an output connection link at the beginning of a workflow subset into an input step */
async function outputConnectionToStep(
    link: ConnectionOutputLink,
    allSteps: Record<number, Step>,
    searchStore: WorkflowSearchStore,
    index: number,
    allStepLabels: Set<string>
): Promise<Step> {
    const outputStep = ensureDefined(allSteps[link.id]);
    const outputConnection = ensureDefined(outputStep.outputs.find((o) => o.name === link.output_name));

    let type: "data_input" | "data_collection_input" | "parameter_input" = "data_input";
    let subType: undefined | "text" | "integer" | "float" | "boolean" | "color" | "directory_uri" = undefined;

    const parameterType = (outputConnection as ParameterOutput).type;

    if ((outputConnection as CollectionOutput).collection) {
        type = "data_collection_input";
    } else if (parameterType && parameterType !== "data") {
        type = "parameter_input";
        subType = parameterType;
    }

    const label = prettifyInputName(type, subType, index, allStepLabels);
    allStepLabels.add(label);

    const position = searchStore.findOutputPosition(link.id, link.output_name);

    assertDefined(position);

    const baseStep = createNewStep(type, type, type, {
        left: position.x + OUTPUT_TO_NODE_POSITION_CORRECTION.left,
        top: position.y + OUTPUT_TO_NODE_POSITION_CORRECTION.top,
    });
    const state = { parameter_type: subType, optional: { optional: outputConnection.optional } };

    const response = await getModule(
        { name: type, type, content_id: type, tool_state: state },
        link.id,
        (_state: boolean) => {}
    );

    const updatedStep = {
        ...baseStep,
        label,
        id: link.id,
        tool_state: response.tool_state,
        inputs: response.inputs,
        outputs: response.outputs,
        config_form: response.config_form,
    };

    return updatedStep;
}

function prettifyOutputName(index: number, allOutputLabels: Set<string>) {
    const getName = (count: number) => `Subworkflow output ${count}`;

    let currentCount = index + 1;
    let currentName = getName(currentCount);

    // increment count to avoid duplicate labels
    while (allOutputLabels.has(currentName)) {
        currentCount += 1;
        currentName = getName(currentCount);
    }

    return currentName;
}

/** converts a set of open ended connections at the end of a workflow subset to workflow outputs */
function outputConnectionsToWorkflowOutputs(
    steps: Step[],
    openConnections: { connection: ConnectionOutputLink; name: string; nodeId: number }[],
    indexOffset = 0
) {
    const newSteps = structuredClone(steps);
    const newConnections: { connection: ConnectionOutputLink; name: string; nodeId: number }[] = [];

    const allOutputLabels = new Set(
        steps.flatMap((step) => {
            if (step.workflow_outputs) {
                return step.workflow_outputs.flatMap((output) => (output.label ? [output.label] : []));
            } else {
                return [];
            }
        })
    );

    openConnections.forEach(({ connection, name, nodeId }, index) => {
        const step = ensureDefined(newSteps.find((step) => step.id === connection.id));

        const existingOutput = step.workflow_outputs?.find((output) => output.output_name === connection.output_name);
        const newOutputName = existingOutput?.output_name ?? prettifyOutputName(index + indexOffset, allOutputLabels);
        allOutputLabels.add(newOutputName);

        if (!existingOutput) {
            step.workflow_outputs = step.workflow_outputs ?? [];
            step.workflow_outputs.push({
                output_name: connection.output_name,
                label: newOutputName,
            });
        }

        const newConnection = {
            connection: {
                ...connection,
                output_name: newOutputName,
            },
            name,
            nodeId,
        };

        newConnections.push(newConnection);
    });

    return { steps: newSteps, connections: newConnections };
}

export type InputReconnectionMap = {
    [label: string]: ConnectionOutputLink;
};

export type OutputReconnectionMap = {
    connection: ConnectionOutputLink;
    name: string;
    nodeId: number;
}[];

export async function convertOpenConnections(
    selectedKeys: number[],
    allSteps: Record<number, Step>,
    searchStore: WorkflowSearchStore
) {
    const selection = selectedKeys.map((key) => ensureDefined(allSteps[key]));

    // convert input connections to input steps

    const openInputConnections = getOpenInputConnections(selectedKeys, allSteps);

    const allLabelsInSelection = new Set(
        selection.flatMap((step) => {
            if (step.label) {
                return [step.label];
            } else {
                return [];
            }
        })
    );

    const inputBaseSteps = await Promise.all(
        openInputConnections.map((connection, index) =>
            outputConnectionToStep(connection, allSteps, searchStore, index, allLabelsInSelection)
        )
    );

    const inputReconnectionMap: InputReconnectionMap = Object.fromEntries(
        inputBaseSteps.map((step, index) => {
            assertDefined(step.label);
            return [step.label, structuredClone(ensureDefined(openInputConnections[index]))];
        })
    );

    // convert output connections to outputs

    const openOutputConnections = getOpenOutputConnections(selectedKeys, allSteps);
    const { steps: modifiedSelection, connections: outputReconnectionMap } = outputConnectionsToWorkflowOutputs(
        selection,
        openOutputConnections
    );

    return { stepArray: [...modifiedSelection, ...inputBaseSteps], inputReconnectionMap, outputReconnectionMap };
}

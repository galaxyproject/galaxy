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

function prettifyName(
    type: "data_input" | "data_collection_input" | "parameter_input",
    subType: undefined | "text" | "integer" | "float" | "boolean" | "color" | "directory_uri",
    index: number
) {
    if (type === "data_input") {
        return `Input Dataset ${index}`;
    } else if (type === "data_collection_input") {
        return `Input Dataset Collection ${index}`;
    } else if (type === "parameter_input") {
        assertDefined(subType);

        return match(subType, {
            boolean: () => `Boolean Input ${index}`,
            color: () => `Color Inputs ${index}`,
            directory_uri: () => `Directory Input ${index}`,
            float: () => `Float Input ${index}`,
            integer: () => `Integer Inputs ${index}`,
            text: () => `Text Inputs ${index}`,
        });
    }
}

// small hardcoded position correction estimate to improve look of input nodes
const OUTPUT_TO_NODE_POSITION_CORRECTION = { top: -73, left: -3 };

async function outputConnectionToStep(
    link: ConnectionOutputLink,
    allSteps: Record<number, Step>,
    searchStore: WorkflowSearchStore,
    index: number
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
        label: prettifyName(type, subType, index),
        id: link.id,
        tool_state: response.tool_state,
        inputs: response.inputs,
        outputs: response.outputs,
        config_form: response.config_form,
    };

    return updatedStep;
}

function inputConnectionsToWorkflowOutputs(
    steps: Step[],
    openConnections: { connection: ConnectionOutputLink; name: string; nodeId: number }[],
    indexOffset = 0
) {
    const newSteps = structuredClone(steps);
    const newConnections: { connection: ConnectionOutputLink; name: string; nodeId: number }[] = [];

    openConnections.forEach(({ connection, name, nodeId }, index) => {
        const step = ensureDefined(newSteps.find((step) => step.id === connection.id));

        const existingOutput = step.workflow_outputs?.find((output) => output.output_name === connection.output_name);
        const newOutputName = existingOutput?.output_name ?? `Subworkflow output ${index + indexOffset}`;

        if (!existingOutput) {
            step.workflow_outputs = step.workflow_outputs ?? [];
            step.workflow_outputs.push({
                output_name: newOutputName,
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

export async function convertOpenConnections(
    selectedKeys: number[],
    allSteps: Record<number, Step>,
    searchStore: WorkflowSearchStore
) {
    const selection = selectedKeys.map((key) => ensureDefined(allSteps[key]));

    // convert input connections to input steps

    const openInputConnections = getOpenInputConnections(selectedKeys, allSteps);

    const inputBaseSteps = await Promise.all(
        openInputConnections.map((connection, index) =>
            outputConnectionToStep(connection, allSteps, searchStore, index)
        )
    );

    const inputReconnectionMap = Object.fromEntries(
        inputBaseSteps.map((step, index) => {
            assertDefined(step.label);
            return [step.label, structuredClone(ensureDefined(openInputConnections[index]))];
        })
    );

    // convert output connections to outputs

    const openOutputConnections = getOpenOutputConnections(selectedKeys, allSteps);
    const { steps: modifiedSelection, connections: outputReconnectionMap } = inputConnectionsToWorkflowOutputs(
        selection,
        openOutputConnections
    );

    return { stepArray: [...modifiedSelection, ...inputBaseSteps], inputReconnectionMap, outputReconnectionMap };
}

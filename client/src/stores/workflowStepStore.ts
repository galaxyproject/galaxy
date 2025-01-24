import { computed, del, ref, set } from "vue";

import { type CollectionTypeDescriptor } from "@/components/Workflow/Editor/modules/collectionTypeDescription";
import { type Connection, getConnectionId, useConnectionStore } from "@/stores/workflowConnectionStore";
import { assertDefined } from "@/utils/assertions";

import { defineScopedStore } from "./scopedStore";
import { useWorkflowStateStore } from "./workflowEditorStateStore";

interface StepPosition {
    top: number;
    left: number;
}

/*
      "ChangeDatatypeActionout_file1": {
        "action_type": "ChangeDatatypeAction",
        "output_name": "out_file1",
        "action_arguments": {
          "newtype": "ab1"
        }
      }
*/

export interface PostJobAction {
    action_type: string;
    output_name: string;
    action_arguments: {
        [index: string]: string;
    };
}

export interface PostJobActions {
    [index: string]: PostJobAction;
}

export interface DataOutput {
    extensions: string[];
    name: string;
    optional: boolean;
}

export interface CollectionOutput extends Omit<DataOutput, "type"> {
    collection: boolean;
    collection_type: string;
    collection_type_source: string | null;
}

export declare const ParameterTypes: "text" | "integer" | "float" | "boolean" | "color" | "data";
export interface ParameterOutput extends Omit<DataOutput, "type" | "extensions"> {
    type: typeof ParameterTypes;
    parameter: true;
    multiple: boolean;
}

interface BaseStepInput {
    valid?: boolean;
    name: string;
    label: string;
    multiple: boolean;
    extensions: string[];
    optional: boolean;
    input_type: string;
    input_subworkflow_step_id?: number;
}

export interface DataStepInput extends BaseStepInput {
    input_type: "dataset";
}

export interface DataCollectionStepInput extends BaseStepInput {
    input_type: "dataset_collection";
    collection_types: string[];
}

export interface ParameterStepInput extends Omit<BaseStepInput, "input_type"> {
    input_type: "parameter";
    type: typeof ParameterTypes;
}

export type InputTerminalSource = DataStepInput | DataCollectionStepInput | ParameterStepInput;
export type OutputTerminalSource = DataOutput | CollectionOutput | ParameterOutput;
export type TerminalSource = InputTerminalSource | OutputTerminalSource;

interface WorkflowOutput {
    output_name: string;
    label?: string | null;
    uuid?: string | null;
}

export interface NewStep {
    annotation?: string;
    config_form?: { [index: string]: any };
    content_id?: string | null;
    id?: number;
    errors?: string[] | null;
    input_connections: StepInputConnection;
    inputs: Array<InputTerminalSource>;
    label?: string | null;
    name: string;
    outputs: Array<OutputTerminalSource>;
    position?: StepPosition;
    post_job_actions?: PostJobActions;
    tool_id?: string;
    tool_state: Record<string, unknown>;
    tool_version?: string;
    tooltip?: string | null;
    type: "tool" | "data_input" | "data_collection_input" | "subworkflow" | "parameter_input" | "pause";
    uuid?: string;
    when?: string | null;
    workflow_id?: string;
    workflow_outputs?: WorkflowOutput[];
}

export interface Step extends NewStep {
    id: number;
}

export interface Steps {
    [index: string]: Step;
}

export interface StepInputConnection {
    [index: string]: ConnectionOutputLink | ConnectionOutputLink[] | undefined;
}

export interface ConnectionOutputLink {
    output_name: string;
    id: number;
    input_subworkflow_step_id?: number;
}

export interface WorkflowOutputs {
    [index: string]: {
        stepId: number;
        outputName: string;
    };
}

interface StepInputMapOver {
    [index: number]: { [index: string]: CollectionTypeDescriptor };
}

export type WorkflowStepStore = ReturnType<typeof useWorkflowStepStore>;

export const useWorkflowStepStore = defineScopedStore("workflowStepStore", (workflowId) => {
    const steps = ref<Steps>({});
    const stepMapOver = ref<{ [index: number]: CollectionTypeDescriptor }>({});
    const stepInputMapOver = ref<StepInputMapOver>({});
    const stepIndex = ref(-1);
    const stepExtraInputs = ref<{ [index: number]: InputTerminalSource[] }>({});

    function $reset() {
        steps.value = {};
        stepMapOver.value = {};
        stepInputMapOver.value = {};
        stepIndex.value = -1;
        stepExtraInputs.value = {};
    }

    const getStep = computed(() => (stepId: number) => steps.value[stepId.toString()]);

    const getStepExtraInputs = computed(() => (stepId: number) => stepExtraInputs.value[stepId] || []);

    const getStepIndex = computed(() =>
        Math.max(...Object.values(steps.value).map((step) => step.id), stepIndex.value)
    );

    const hasActiveOutputs = computed(() =>
        Boolean(Object.values(steps.value).find((step) => step.workflow_outputs?.length))
    );

    const workflowOutputs = computed(() => {
        const workflowOutputs: WorkflowOutputs = {};

        Object.values(steps.value).forEach((step) => {
            if (step.workflow_outputs?.length) {
                step.workflow_outputs.forEach((workflowOutput) => {
                    if (workflowOutput.label) {
                        workflowOutputs[workflowOutput.label] = {
                            outputName: workflowOutput.output_name,
                            stepId: step.id,
                        };
                    }
                });
            }
        });

        return workflowOutputs;
    });

    const duplicateLabels = computed(() => {
        const duplicateLabels: Set<string> = new Set();
        const labels: Set<string> = new Set();

        Object.values(steps.value).forEach((step) => {
            if (step.workflow_outputs?.length) {
                step.workflow_outputs.forEach((workflowOutput) => {
                    if (workflowOutput.label) {
                        if (labels.has(workflowOutput.label)) {
                            duplicateLabels.add(workflowOutput.label);
                        }
                        labels.add(workflowOutput.label);
                    }
                });
            }
        });

        return duplicateLabels;
    });

    const connectionStore = useConnectionStore(workflowId);

    const stateStore = useWorkflowStateStore(workflowId);

    function addStep(newStep: NewStep, select = false, createConnections = true): Step {
        const stepId = newStep.id ?? getStepIndex.value + 1;
        const step = Object.freeze({ ...newStep, id: stepId } as Step);

        set(steps.value, stepId.toString(), step);

        if (createConnections) {
            stepToConnections(step).forEach((connection) => connectionStore.addConnection(connection));
        }

        stepExtraInputs.value[step.id] = findStepExtraInputs(step);

        if (select) {
            stateStore.setStepMultiSelected(step.id, true);
        }

        return step;
    }

    function insertNewStep(
        contentId: NewStep["content_id"],
        name: NewStep["name"],
        type: NewStep["type"],
        position: NewStep["position"]
    ) {
        const stepData: NewStep = {
            name: name,
            content_id: contentId,
            input_connections: {},
            type: type,
            inputs: [],
            outputs: [],
            position: position,
            post_job_actions: {},
            tool_state: {},
        };

        return addStep(stepData);
    }

    function updateStep(step: Step) {
        const workflow_outputs = step.workflow_outputs?.filter((workflowOutput) =>
            step.outputs.find((output) => workflowOutput.output_name == output.name)
        );

        steps.value[step.id.toString()] = Object.freeze({ ...step, workflow_outputs });
        stepExtraInputs.value[step.id] = findStepExtraInputs(step);
    }

    function updateStepValue<K extends keyof Step>(stepId: number, key: K, value: Step[K]) {
        const step = steps.value[stepId];
        assertDefined(step);

        const partialStep: Partial<Step> = {};
        partialStep[key] = value;

        updateStep({ ...step, ...partialStep });
    }

    function changeStepMapOver(stepId: number, mapOver: CollectionTypeDescriptor) {
        set(stepMapOver.value, stepId, mapOver);
    }

    function resetStepInputMapOver(stepId: number) {
        set(stepInputMapOver.value, stepId, {});
    }

    function changeStepInputMapOver(stepId: number, inputName: string, mapOver: CollectionTypeDescriptor) {
        if (stepInputMapOver.value[stepId]) {
            set(stepInputMapOver.value[stepId]!, inputName, mapOver);
        } else {
            set(stepInputMapOver.value, stepId, { [inputName]: mapOver });
        }
    }

    function addConnection(connection: Connection) {
        const inputStep = getStep.value(connection.input.stepId);

        assertDefined(
            inputStep,
            `Failed to add connection, because step with id ${connection.input.stepId} is undefined`
        );

        const input = inputStep.inputs.find((input) => input.name === connection.input.name);
        const connectionLink: ConnectionOutputLink = {
            output_name: connection.output.name,
            id: connection.output.stepId,
        };

        if (input && "input_subworkflow_step_id" in input && input.input_subworkflow_step_id !== undefined) {
            connectionLink["input_subworkflow_step_id"] = input.input_subworkflow_step_id;
        }

        let connectionLinks: ConnectionOutputLink[] = [connectionLink];
        let inputConnection = inputStep.input_connections[connection.input.name];

        if (inputConnection) {
            if (!Array.isArray(inputConnection)) {
                inputConnection = [inputConnection];
            }
            inputConnection = inputConnection.filter(
                (connection) =>
                    !(connection.id === connectionLink.id && connection.output_name === connectionLink.output_name)
            );
            connectionLinks = [...connectionLinks, ...inputConnection];
        }

        const updatedStep = {
            ...inputStep,
            input_connections: {
                ...inputStep.input_connections,
                [connection.input.name]: connectionLinks.sort((a, b) =>
                    a.id === b.id ? a.output_name.localeCompare(b.output_name) : a.id - b.id
                ),
            },
        };

        updateStep(updatedStep);
    }

    function removeConnection(connection: Connection) {
        const inputStep = getStep.value(connection.input.stepId);

        assertDefined(
            inputStep,
            `Failed to remove connection, because step with id ${connection.input.stepId} is undefined`
        );

        const inputConnections = inputStep.input_connections[connection.input.name];

        if (getStepExtraInputs.value(inputStep.id).find((input) => connection.input.name === input.name)) {
            inputStep.input_connections[connection.input.name] = undefined;
        } else {
            if (Array.isArray(inputConnections)) {
                inputStep.input_connections[connection.input.name] = inputConnections.filter(
                    (outputLink) =>
                        !(outputLink.id === connection.output.stepId, outputLink.output_name === connection.output.name)
                );
            } else {
                del(inputStep.input_connections, connection.input.name);
            }
        }

        updateStep(inputStep);
    }

    const { deleteStepPosition, deleteStepTerminals } = useWorkflowStateStore(workflowId);

    function removeStep(stepId: number) {
        connectionStore
            .getConnectionsForStep(stepId)
            .forEach((connection) => connectionStore.removeConnection(getConnectionId(connection)));

        del(steps.value, stepId.toString());
        del(stepExtraInputs.value, stepId);
        del(stateStore.multiSelectedSteps, stepId);
        del(stepMapOver.value, stepId.toString());

        deleteStepPosition(stepId);
        deleteStepTerminals(stepId);
    }

    return {
        steps,
        stepMapOver,
        stepInputMapOver,
        stepIndex,
        stepExtraInputs,
        $reset,
        getStep,
        getStepExtraInputs,
        getStepIndex,
        hasActiveOutputs,
        workflowOutputs,
        duplicateLabels,
        addStep,
        insertNewStep,
        updateStep,
        updateStepValue,
        changeStepMapOver,
        resetStepInputMapOver,
        changeStepInputMapOver,
        addConnection,
        removeConnection,
        removeStep,
    };
});

function makeConnection(inputId: number, inputName: string, outputId: number, outputName: string): Connection {
    return {
        input: {
            stepId: inputId,
            name: inputName,
            connectorType: "input",
        },
        output: {
            stepId: outputId,
            name: outputName,
            connectorType: "output",
        },
    };
}

function stepToConnections(step: Step): Connection[] {
    const connections: Connection[] = [];

    if (step.input_connections) {
        Object.entries(step?.input_connections).forEach(([inputName, outputArray]) => {
            if (outputArray === undefined) {
                return;
            }
            if (!Array.isArray(outputArray)) {
                outputArray = [outputArray];
            }
            outputArray.forEach((output) => {
                const connection = makeConnection(step.id, inputName, output.id, output.output_name);
                const connectionInput = step.inputs.find((input) => input.name == inputName);
                if (connectionInput && "input_subworkflow_step_id" in connectionInput) {
                    connection.input.input_subworkflow_step_id = connectionInput.input_subworkflow_step_id;
                }
                connections.push(connection);
            });
        });
    }

    return connections;
}

function findStepExtraInputs(step: Step) {
    const extraInputs: InputTerminalSource[] = [];
    if (step.when !== undefined) {
        Object.keys(step.input_connections).forEach((inputName) => {
            if (!step.inputs.find((input) => input.name === inputName) && step.when?.includes(inputName)) {
                const terminalSource = {
                    name: inputName,
                    optional: false,
                    input_type: "parameter" as const,
                    type: "boolean" as const,
                    multiple: false,
                    label: inputName,
                    extensions: [],
                };
                extraInputs.push(terminalSource);
            }
        });
    }
    return extraInputs;
}

import Vue from "vue";
import { defineStore } from "pinia";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { Connection } from "@/stores/workflowConnectionStore";
import type { CollectionTypeDescriptor } from "@/components/Workflow/Editor/modules/collectionTypeDescription";

interface State {
    steps: { [index: string]: Step };
    stepIndex: number;
    stepMapOver: { [index: number]: CollectionTypeDescriptor };
}

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
    activeOutput?: boolean;
}

export interface CollectionOutput extends Omit<DataOutput, "type"> {
    collection: boolean;
    collection_type: string;
    collection_type_source: string | null;
}

export declare const ParameterTypes: "text" | "integer" | "float" | "boolean" | "color";
export interface ParameterOutput extends Omit<DataOutput, "type" | "extensions"> {
    type: typeof ParameterTypes;
    parameter: true;
}

interface BaseStepInput {
    name: string;
    label: string;
    multiple: boolean;
    extensions: string[];
    optional: boolean;
    input_type: string;
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

type InputTerminalSource = DataStepInput | DataCollectionStepInput | ParameterStepInput;
type OutputTerminalSource = DataOutput | CollectionOutput | ParameterOutput;
export type TerminalSource = InputTerminalSource | OutputTerminalSource;

interface WorkflowOutput {
    output_name: string;
    label?: string;
    uuid?: string;
}

export interface NewStep {
    annotation?: string;
    config_form?: { [index: string]: any };
    content_id?: string | null;
    id?: number;
    errors?: string[] | null;
    input_connections: StepInputConnection;
    inputs: Array<InputTerminalSource>;
    label?: string;
    name: string;
    outputs: Array<OutputTerminalSource>;
    position?: StepPosition;
    post_job_actions?: PostJobActions;
    tool_state: Record<string, unknown>;
    tooltip?: string;
    type: "tool" | "data_input" | "data_collection_input" | "subworkflow" | "parameter_input" | "pause";
    uuid?: string;
    workflow_outputs?: WorkflowOutput[];
}

export interface Step extends NewStep {
    id: number;
}

export interface Steps {
    [index: string]: Step;
}

export interface StepInputConnection {
    [index: string]: ConnectionOutputLink | ConnectionOutputLink[];
}

interface ConnectionOutputLink {
    output_name: string;
    id: number;
}

interface WorkflowOutputs {
    [index: string]: {
        stepId: number;
        outputName: string;
    };
}

export const useWorkflowStepStore = defineStore("workflowStepStore", {
    state: (): State => ({
        steps: {} as Steps,
        stepMapOver: {} as { [index: number]: CollectionTypeDescriptor },
        stepIndex: -1,
    }),
    getters: {
        getStep(state: State) {
            return (stepId: number): Step => {
                return state.steps[stepId.toString()];
            };
        },
        getStepIndex(state: State) {
            return Math.max(...Object.entries(state.steps).map(([_, step]) => step.id), state.stepIndex);
        },
        workflowOutputs(state: State) {
            const workflowOutputs: WorkflowOutputs = {};
            Object.values(state.steps).forEach((step) => {
                if (step.workflow_outputs?.length) {
                    step.workflow_outputs.forEach((workflowOutput) => {
                        workflowOutputs[workflowOutput.label || workflowOutput.output_name] = {
                            outputName: workflowOutput.output_name,
                            stepId: step.id,
                        };
                    });
                }
            });
            return workflowOutputs;
        },
    },
    actions: {
        addStep(newStep: NewStep): Step {
            const stepId = newStep.id ? newStep.id : this.getStepIndex + 1;
            newStep.id = stepId;
            const step = newStep as Step;
            Vue.set(this.steps, stepId.toString(), step);
            const connectionStore = useConnectionStore();
            stepToConnections(step).map((connection) => connectionStore.addConnection(connection));
            return step;
        },
        updateStep(this: State, step: Step) {
            this.steps[step.id.toString()] = step;
        },
        changeStepMapOver(stepId: number, mapOver: CollectionTypeDescriptor) {
            this.stepMapOver[stepId] = mapOver;
        },
        addConnection(connection: Connection) {
            const inputStep = this.getStep(connection.input.stepId);
            const updatedStep = {
                ...inputStep,
                input_connections: {
                    ...inputStep.input_connections,
                    [connection.input.name]: { output_name: connection.output.name, id: connection.output.stepId },
                },
            };
            this.updateStep(updatedStep);
        },
        removeConnection(connection: Connection) {
            const inputStep = this.getStep(connection.input.stepId);
            Vue.delete(inputStep.input_connections, connection.input.name);
            this.updateStep(inputStep);
        },
        removeStep(this: State, stepId: number) {
            const connectionStore = useConnectionStore();
            connectionStore
                .getConnectionsForStep(stepId)
                .map((connection) => connectionStore.removeConnection(connection.input));
            Vue.delete(this.steps, stepId.toString());
        },
    },
});

export function stepToConnections(step: Step): Connection[] {
    const connections: Connection[] = [];
    if (step.input_connections) {
        Object.entries(step?.input_connections).forEach(([input_name, outputArray]) => {
            if (!Array.isArray(outputArray)) {
                outputArray = [outputArray];
            }
            outputArray.forEach((output) => {
                const connection = new Connection(
                    {
                        stepId: step.id,
                        name: input_name,
                        connectorType: "input",
                    },
                    {
                        stepId: output.id,
                        name: output.output_name,
                        connectorType: "output",
                    }
                );
                connections.push(connection);
            });
        });
    }
    return connections;
}

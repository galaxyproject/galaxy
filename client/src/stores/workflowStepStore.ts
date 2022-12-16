import Vue, { type Data } from "vue";
import { defineStore } from "pinia";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import type { Connection } from "@/stores/workflowConnectionStore";
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

interface PostJobActions {
    [index: string]: {
        action_type: string;
        output_name: string;
        action_arguments: {
            newtype: string;
        };
    };
}

interface DataOutput {
    extensions: string[];
    name: string;
    optional: boolean;
    type?: string;
    activeOutput?: boolean;
    input_type?: string;
}

interface CollectionOutput extends DataOutput {
    collection: boolean;
    collection_type: string;
}

export interface NewStep {
    annotation?: string;
    config_form?: object;
    content_id?: string | null;
    id?: number;
    input_connections: StepInputConnection;
    inputs: any;
    label?: string;
    name: string;
    outputs: Array<DataOutput | CollectionOutput>;
    position?: StepPosition;
    post_job_actions: PostJobActions;
    tool_state: Record<string, unknown>;
    tooltip?: string;
    type: string;
    uuid?: string;
    workflow_outputs: Array<any>;
}

export interface Step extends NewStep {
    id: number;
}

export interface StepInputConnection {
    [index: string]: ConnectionOutputLink | ConnectionOutputLink[];
}

interface ConnectionOutputLink {
    output_name: string;
    id: number;
}

export const useWorkflowStepStore = defineStore("workflowStepStore", {
    state: (): State => ({
        steps: {} as { [index: string]: Step },
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
    },
    actions: {
        addStep(newStep: NewStep): Step {
            const stepId = newStep.id ? newStep.id : this.getStepIndex + 1;
            newStep.id = stepId;
            const step = newStep as Step;
            console.log("adding step", step.id);
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
                const connection: Connection = {
                    id: `${step.id}-${input_name}-${output.id}-${output.output_name}`,
                    input: {
                        stepId: step.id,
                        name: input_name,
                        connectorType: "input",
                    },
                    output: {
                        stepId: output.id,
                        name: output.output_name,
                        connectorType: "output",
                    },
                };
                connections.push(connection);
            });
        });
    }
    return connections;
}

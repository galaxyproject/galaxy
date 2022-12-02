import { setActivePinia, createPinia } from "pinia";

import { useWorkflowStepStore } from "stores/workflowStepStore";
import { useConnectionStore } from "./workflowConnectionStore";
import type { Step, StepInputConnection } from "stores/workflowStepStore";

const stepInputConnection: StepInputConnection = {
    "1": {
        output_name: "output",
        id: 0,
    },
};

const workflowStepZero: Step = {
    input_connections: {},
    inputs: [],
    name: "a step",
    outputs: [],
    post_job_actions: {},
    tool_state: {},
    type: "tool",
    workflow_outputs: [],
};

const workflowStepOne: Step = { ...workflowStepZero, input_connections: stepInputConnection };

describe("Connection Store", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("adds step", () => {
        const stepStore = useWorkflowStepStore();
        expect(stepStore.steps).toStrictEqual({});
        stepStore.addStep(workflowStepZero);
        expect(stepStore.getStep(0)).toBe(workflowStepZero);
        expect(workflowStepZero.id).toBe(0);
    });
    it("removes step", () => {
        const stepStore = useWorkflowStepStore();
        stepStore.addStep(workflowStepZero);
        stepStore.removeStep(workflowStepZero.id);
        expect(stepStore.getStep[0]).toBe(undefined);
    });
    it("creates connection if step has connection", () => {
        const stepStore = useWorkflowStepStore();
        const connectionStore = useConnectionStore();
        stepStore.addStep(workflowStepZero);
        stepStore.addStep(workflowStepOne);
        expect(connectionStore.connections.length).toBe(1);
    });
    it("removes connection if step has connection", () => {
        const stepStore = useWorkflowStepStore();
        const connectionStore = useConnectionStore();
        stepStore.addStep(workflowStepZero);
        stepStore.addStep(workflowStepOne);
        expect(connectionStore.connections.length).toBe(1);
        stepStore.removeStep(workflowStepOne.id);
        expect(connectionStore.connections.length).toBe(0);
    });
});

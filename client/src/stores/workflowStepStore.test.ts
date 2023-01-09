import { setActivePinia, createPinia } from "pinia";

import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { useConnectionStore } from "./workflowConnectionStore";
import type { NewStep, StepInputConnection } from "@/stores/workflowStepStore";

const stepInputConnection: StepInputConnection = {
    "1": {
        output_name: "output",
        id: 0,
    },
};

const workflowStepZero: NewStep = {
    input_connections: {},
    inputs: [],
    name: "a step",
    outputs: [],
    post_job_actions: {},
    tool_state: {},
    type: "tool",
    workflow_outputs: [],
};

const workflowStepOne: NewStep = { ...workflowStepZero, input_connections: stepInputConnection };

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
        const addedStep = stepStore.addStep(workflowStepZero);
        expect(addedStep.id).toBe(0);
        stepStore.removeStep(addedStep.id);
        expect(stepStore.getStep(0)).toBe(undefined);
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
        const stepOne = stepStore.addStep(workflowStepOne);
        expect(connectionStore.connections.length).toBe(1);
        stepStore.removeStep(stepOne.id);
        expect(connectionStore.connections.length).toBe(0);
    });
});

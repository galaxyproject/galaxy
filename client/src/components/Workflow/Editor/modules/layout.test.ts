import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type InputTerminalSource, type NewStep, useWorkflowStepStore } from "@/stores/workflowStepStore";

import { autoLayout } from "./layout";

// Helper to create a minimal step with position
function createStep(
    id: number,
    options: {
        inputs?: InputTerminalSource[];
        when?: string;
        inputConnections?: NewStep["input_connections"];
    } = {},
): NewStep {
    return {
        id,
        name: `Step ${id}`,
        type: "tool",
        inputs: options.inputs ?? [],
        outputs: [
            {
                name: "output",
                extensions: ["txt"],
                optional: false,
            },
        ],
        input_connections: options.inputConnections ?? {},
        position: { left: id * 200, top: 100 },
        post_job_actions: {},
        tool_state: {},
        workflow_outputs: [],
        when: options.when,
    };
}

describe("layout.ts", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    describe("autoLayout with conditional steps", () => {
        it("handles steps with 'when' conditional inputs without crashing", async () => {
            const workflowId = "test-workflow";
            const stepStore = useWorkflowStepStore(workflowId);
            const stateStore = useWorkflowStateStore(workflowId);

            // Create a boolean parameter step (source)
            const paramStep = stepStore.addStep(
                createStep(0, {
                    outputs: [
                        {
                            name: "output",
                            extensions: [],
                            optional: false,
                            type: "boolean",
                            parameter: true,
                            multiple: false,
                        },
                    ],
                }),
            );

            // Create a tool step with conditional execution
            const conditionalStep = stepStore.addStep(
                createStep(1, {
                    inputs: [
                        {
                            name: "input_file",
                            label: "Input File",
                            multiple: false,
                            optional: false,
                            extensions: ["txt"],
                            input_type: "dataset",
                        },
                    ],
                    when: "${check_value}",
                    inputConnections: {
                        check_value: { output_name: "output", id: 0 },
                    },
                }),
            );

            // Set up step positions in state store
            stateStore.stepPosition[paramStep.id] = { width: 180, height: 50 };
            stateStore.stepPosition[conditionalStep.id] = { width: 180, height: 80 };

            const steps = {
                [paramStep.id]: paramStep,
                [conditionalStep.id]: conditionalStep,
            };

            // This should not throw "Referenced shape does not exist" error
            const result = await autoLayout(workflowId, steps, []);

            expect(result).toBeDefined();
            expect(result?.steps).toHaveLength(2);
        });

        it("handles multiple conditional steps", async () => {
            const workflowId = "test-workflow-multi";
            const stepStore = useWorkflowStepStore(workflowId);
            const stateStore = useWorkflowStateStore(workflowId);

            // Source step
            const sourceStep = stepStore.addStep(createStep(0));

            // First conditional step
            const cond1 = stepStore.addStep(
                createStep(1, {
                    when: "${flag1}",
                    inputConnections: { flag1: { output_name: "output", id: 0 } },
                }),
            );

            // Second conditional step
            const cond2 = stepStore.addStep(
                createStep(2, {
                    when: "${flag2}",
                    inputConnections: { flag2: { output_name: "output", id: 0 } },
                }),
            );

            stateStore.stepPosition[sourceStep.id] = { width: 180, height: 50 };
            stateStore.stepPosition[cond1.id] = { width: 180, height: 50 };
            stateStore.stepPosition[cond2.id] = { width: 180, height: 50 };

            const steps = {
                [sourceStep.id]: sourceStep,
                [cond1.id]: cond1,
                [cond2.id]: cond2,
            };

            const result = await autoLayout(workflowId, steps, []);

            expect(result).toBeDefined();
            expect(result?.steps).toHaveLength(3);
        });
    });

    describe("edge validation", () => {
        it("filters out edges with orphaned connections", async () => {
            const workflowId = "test-workflow-orphan";
            const stepStore = useWorkflowStepStore(workflowId);
            const stateStore = useWorkflowStateStore(workflowId);

            // Create a step with an input that doesn't exist on the step
            // This simulates an orphaned connection from workflow import
            const step0 = stepStore.addStep(createStep(0));
            const step1 = stepStore.addStep(
                createStep(1, {
                    // Input connections reference a non-existent input
                    inputConnections: {
                        nonexistent_input: { output_name: "output", id: 0 },
                    },
                }),
            );

            stateStore.stepPosition[step0.id] = { width: 180, height: 50 };
            stateStore.stepPosition[step1.id] = { width: 180, height: 50 };

            const steps = {
                [step0.id]: step0,
                [step1.id]: step1,
            };

            // Spy on console.warn to verify warning is logged
            const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

            const result = await autoLayout(workflowId, steps, []);

            // Should complete without error
            expect(result).toBeDefined();
            expect(result?.steps).toHaveLength(2);

            // Should have logged a warning about the orphaned edge
            expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining("Auto Layout: skipping edge"));

            warnSpy.mockRestore();
        });

        it("does not filter valid edges", async () => {
            const workflowId = "test-workflow-valid";
            const stepStore = useWorkflowStepStore(workflowId);
            const stateStore = useWorkflowStateStore(workflowId);

            const step0 = stepStore.addStep(createStep(0));
            const step1 = stepStore.addStep(
                createStep(1, {
                    inputs: [
                        {
                            name: "input_file",
                            label: "Input",
                            multiple: false,
                            optional: false,
                            extensions: ["txt"],
                            input_type: "dataset",
                        },
                    ],
                    inputConnections: {
                        input_file: { output_name: "output", id: 0 },
                    },
                }),
            );

            stateStore.stepPosition[step0.id] = { width: 180, height: 50 };
            stateStore.stepPosition[step1.id] = { width: 180, height: 50 };

            const steps = {
                [step0.id]: step0,
                [step1.id]: step1,
            };

            const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

            const result = await autoLayout(workflowId, steps, []);

            expect(result).toBeDefined();
            // No warning should be logged for valid edges
            expect(warnSpy).not.toHaveBeenCalled();

            warnSpy.mockRestore();
        });
    });
});

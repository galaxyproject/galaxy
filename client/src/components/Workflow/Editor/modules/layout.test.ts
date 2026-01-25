import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

import { createMockStepPosition, createTestStep } from "../test_fixtures";
import { AUTO_LAYOUT_ORPHAN_EDGE_WARNING_PREFIX, autoLayout } from "./layout";

type LayoutResult = Awaited<ReturnType<typeof autoLayout>>;

/** Asserts target step is positioned to the right of source step (proves edge exists in graph) */
function expectStepToRightOf(result: LayoutResult, targetStepId: number, sourceStepId: number) {
    const sourcePos = result?.steps.find((s) => s.id === String(sourceStepId));
    const targetPos = result?.steps.find((s) => s.id === String(targetStepId));
    expect(sourcePos, `Step ${sourceStepId} not in layout result`).toBeDefined();
    expect(targetPos, `Step ${targetStepId} not in layout result`).toBeDefined();
    expect(targetPos!.x).toBeGreaterThan(sourcePos!.x);
}

describe("layout.ts", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe("autoLayout with conditional steps", () => {
        it("handles steps with 'when' conditional inputs without crashing", async () => {
            const workflowId = "test-workflow";
            const stepStore = useWorkflowStepStore(workflowId);
            const stateStore = useWorkflowStateStore(workflowId);

            // Create a boolean parameter step (source)
            const paramStep = stepStore.addStep(
                createTestStep(0, {
                    outputs: [
                        {
                            name: "output",
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
                createTestStep(1, {
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
            stateStore.stepPosition[paramStep.id] = createMockStepPosition(180, 50);
            stateStore.stepPosition[conditionalStep.id] = createMockStepPosition(180, 80);

            const steps = {
                [paramStep.id]: paramStep,
                [conditionalStep.id]: conditionalStep,
            };

            // This should not throw "Referenced shape does not exist" error
            const result = await autoLayout(workflowId, steps, []);

            expect(result).toBeDefined();
            expect(result?.steps).toHaveLength(2);

            // Connected step should be to the right of source (proves conditional edge was included)
            expectStepToRightOf(result, conditionalStep.id, paramStep.id);
        });

        it("handles multiple conditional steps", async () => {
            const workflowId = "test-workflow-multi";
            const stepStore = useWorkflowStepStore(workflowId);
            const stateStore = useWorkflowStateStore(workflowId);

            // Source step
            const sourceStep = stepStore.addStep(createTestStep(0));

            // First conditional step
            const cond1 = stepStore.addStep(
                createTestStep(1, {
                    when: "${flag1}",
                    inputConnections: { flag1: { output_name: "output", id: 0 } },
                }),
            );

            // Second conditional step
            const cond2 = stepStore.addStep(
                createTestStep(2, {
                    when: "${flag2}",
                    inputConnections: { flag2: { output_name: "output", id: 0 } },
                }),
            );

            stateStore.stepPosition[sourceStep.id] = createMockStepPosition(180, 50);
            stateStore.stepPosition[cond1.id] = createMockStepPosition(180, 50);
            stateStore.stepPosition[cond2.id] = createMockStepPosition(180, 50);

            const steps = {
                [sourceStep.id]: sourceStep,
                [cond1.id]: cond1,
                [cond2.id]: cond2,
            };

            const result = await autoLayout(workflowId, steps, []);

            expect(result).toBeDefined();
            expect(result?.steps).toHaveLength(3);

            // Both conditional steps should be to the right of source
            expectStepToRightOf(result, cond1.id, sourceStep.id);
            expectStepToRightOf(result, cond2.id, sourceStep.id);
        });
    });

    describe("edge validation", () => {
        it("filters out edges with orphaned connections", async () => {
            const workflowId = "test-workflow-orphan";
            const stepStore = useWorkflowStepStore(workflowId);
            const stateStore = useWorkflowStateStore(workflowId);

            // Create a step with an input that doesn't exist on the step
            // This simulates an orphaned connection from workflow import
            const step0 = stepStore.addStep(createTestStep(0));
            const step1 = stepStore.addStep(
                createTestStep(1, {
                    // Input connections reference a non-existent input
                    inputConnections: {
                        nonexistent_input: { output_name: "output", id: 0 },
                    },
                }),
            );

            stateStore.stepPosition[step0.id] = createMockStepPosition(180, 50);
            stateStore.stepPosition[step1.id] = createMockStepPosition(180, 50);

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
            expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining(AUTO_LAYOUT_ORPHAN_EDGE_WARNING_PREFIX));
        });

        it("does not filter valid edges", async () => {
            const workflowId = "test-workflow-valid";
            const stepStore = useWorkflowStepStore(workflowId);
            const stateStore = useWorkflowStateStore(workflowId);

            const step0 = stepStore.addStep(createTestStep(0));
            const step1 = stepStore.addStep(
                createTestStep(1, {
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

            stateStore.stepPosition[step0.id] = createMockStepPosition(180, 50);
            stateStore.stepPosition[step1.id] = createMockStepPosition(180, 50);

            const steps = {
                [step0.id]: step0,
                [step1.id]: step1,
            };

            const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

            const result = await autoLayout(workflowId, steps, []);

            expect(result).toBeDefined();
            // No warning should be logged for valid edges
            expect(warnSpy).not.toHaveBeenCalled();

            // Valid edge was used in layout
            expectStepToRightOf(result, step1.id, step0.id);
        });
    });
});

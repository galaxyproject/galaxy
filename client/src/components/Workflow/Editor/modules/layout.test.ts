import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type InputTerminalSource, type NewStep, type Step, useWorkflowStepStore } from "@/stores/workflowStepStore";

import { createMockStepPosition, createTestStep } from "../test_fixtures";
import { AUTO_LAYOUT_ORPHAN_EDGE_WARNING_PREFIX, autoLayout } from "./layout";

type LayoutResult = Awaited<ReturnType<typeof autoLayout>>;

const WORKFLOW_ID = "test-workflow";
const STEP_WIDTH = 180;
const STEP_HEIGHT = 50;

/**
 * Adds the steps to the workflow, gives each the size the editor would measure
 * from the DOM (`heights` overrides it per step ID), and auto-lays them out.
 */
async function layOutSteps(newSteps: NewStep[], heights: Record<number, number> = {}) {
    const stepStore = useWorkflowStepStore(WORKFLOW_ID);
    const stateStore = useWorkflowStateStore(WORKFLOW_ID);
    const steps: Record<string, Step> = {};
    for (const newStep of newSteps) {
        const step = stepStore.addStep(newStep);
        stateStore.stepPosition[step.id] = createMockStepPosition(STEP_WIDTH, heights[step.id] ?? STEP_HEIGHT);
        steps[step.id] = step;
    }
    return autoLayout(WORKFLOW_ID, steps, []);
}

function datasetInput(name: string, label: string): InputTerminalSource {
    return { name, label, multiple: false, optional: false, extensions: ["txt"], input_type: "dataset" };
}

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
        it("lays out a step whose 'when' input is connected to a boolean parameter", async () => {
            const booleanParameter = createTestStep(0, {
                outputs: [{ name: "output", optional: false, type: "boolean", parameter: true, multiple: false }],
            });
            const conditionalStep = createTestStep(1, {
                inputs: [datasetInput("input_file", "Input File")],
                when: "$(inputs.check_value)",
                inputConnections: { check_value: { output_name: "output", id: 0 } },
            });

            // Would fail with "Referenced shape does not exist" if the conditional input had no port
            const result = await layOutSteps([booleanParameter, conditionalStep], { 1: 80 });

            expect(result).toBeDefined();
            expect(result?.steps).toHaveLength(2);
            expectStepToRightOf(result, 1, 0);
        });

        it("lays out several conditional steps driven by the same source", async () => {
            const result = await layOutSteps([
                createTestStep(0),
                createTestStep(1, {
                    when: "$(inputs.flag1)",
                    inputConnections: { flag1: { output_name: "output", id: 0 } },
                }),
                createTestStep(2, {
                    when: "$(inputs.flag2)",
                    inputConnections: { flag2: { output_name: "output", id: 0 } },
                }),
            ]);

            expect(result).toBeDefined();
            expect(result?.steps).toHaveLength(3);
            expectStepToRightOf(result, 1, 0);
            expectStepToRightOf(result, 2, 0);
        });
    });

    describe("edge validation", () => {
        it("skips and warns about a connection to an input the step does not have", async () => {
            const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

            // As can happen with connections left over in an imported workflow
            const result = await layOutSteps([
                createTestStep(0),
                createTestStep(1, { inputConnections: { nonexistent_input: { output_name: "output", id: 0 } } }),
            ]);

            expect(result).toBeDefined();
            expect(result?.steps).toHaveLength(2);
            expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining(AUTO_LAYOUT_ORPHAN_EDGE_WARNING_PREFIX));
        });

        it("lays out a connection to an existing input without warning", async () => {
            const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

            const result = await layOutSteps([
                createTestStep(0),
                createTestStep(1, {
                    inputs: [datasetInput("input_file", "Input")],
                    inputConnections: { input_file: { output_name: "output", id: 0 } },
                }),
            ]);

            expect(result).toBeDefined();
            expect(warnSpy).not.toHaveBeenCalled();
            expectStepToRightOf(result, 1, 0);
        });
    });
});

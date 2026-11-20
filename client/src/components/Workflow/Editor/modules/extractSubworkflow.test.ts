import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { mockToolStep } from "@/components/Workflow/Editor/Actions/mockData";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { Step } from "@/stores/workflowStepStore";

import { extractSubworkflow } from "./extractSubworkflow";

vi.mock("@/components/Workflow/Editor/modules/services", () => ({
    getModule: vi.fn(async () => ({
        tool_state: {},
        inputs: [],
        outputs: [{ name: "output", extensions: ["input"], optional: false }],
        config_form: {},
    })),
}));

const workflowId = "mock-workflow";

describe("extractSubworkflow", () => {
    let stores: ReturnType<typeof useWorkflowStores>;

    beforeEach(() => {
        setActivePinia(createPinia());
        stores = useWorkflowStores(workflowId);
        vi.spyOn(stores.searchStore, "findOutputPosition").mockReturnValue({ x: 0, y: 0 } as never);

        // input 0 feeds tool 1 (to be moved) and tool 2 (stays outside)
        const fromInput = { input1: [{ id: 0, output_name: "output" }] };
        const input: Step = {
            ...mockToolStep(0),
            type: "data_input",
            input_connections: {},
            outputs: [{ name: "output", extensions: ["input"], optional: false }],
        };
        [
            input,
            { ...mockToolStep(1), input_connections: fromInput },
            { ...mockToolStep(2), input_connections: fromInput },
        ].forEach((step) => stores.stepStore.addStep(step));
    });

    it("keeps selected input steps in the parent and feeds them in through a generated input", async () => {
        stores.stateStore.setStepMultiSelected(0, true);
        stores.stateStore.setStepMultiSelected(1, true);

        const { partialWorkflow, inputReconnectionMap, keptInputSteps } = await extractSubworkflow(workflowId, "Sub");

        expect([...keptInputSteps]).toEqual([0]);
        expect(Object.values(partialWorkflow.steps).map((step) => step.id)).not.toContain(0);
        expect(inputReconnectionMap.map(({ connection }) => connection)).toEqual([{ id: 0, output_name: "output" }]);
        expect(stores.stateStore.multiSelectedStepIds).toEqual([1]);
    });

    it("refuses a selection of only input steps", async () => {
        stores.stateStore.setStepMultiSelected(0, true);

        await expect(extractSubworkflow(workflowId, "Sub")).rejects.toThrow("not a workflow input");
    });
});

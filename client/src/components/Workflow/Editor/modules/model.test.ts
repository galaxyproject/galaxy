import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useWorkflowCommentStore } from "@/stores/workflowEditorCommentStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

import { createTestStep } from "../test_fixtures";
import { fromSimple } from "./model";

type Workflow = Parameters<typeof fromSimple>[1];

/** Two steps in one frame; steps listed in `unpositioned` (and the frame, if any step is) have no geometry. */
function workflow(unpositioned: number[], stepIds = [0, 1]): Workflow {
    const steps = Object.fromEntries(
        stepIds.map((id) => {
            const step = createTestStep(id);
            return [id, unpositioned.includes(id) ? { ...step, position: undefined } : step];
        }),
    );
    const frame = { id: 0, type: "frame", color: "none", data: { title: "QC" }, child_steps: stepIds };
    const comments = stepIds.length
        ? [unpositioned.length ? frame : { ...frame, position: [0, 0], size: [500, 300] }]
        : [];
    return { steps, comments, report: { markdown: "" } } as unknown as Workflow;
}

describe("fromSimple without positions", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("parks steps and frames at the origin and asks for a first layout", async () => {
        await fromSimple("wf-unlaid", workflow([0, 1]));
        expect(useWorkflowStateStore("wf-unlaid").needsInitialLayout).toBe(true);
        expect(useWorkflowStepStore("wf-unlaid").steps[0]?.position).toEqual({ left: 0, top: 0 });
        const [frame] = useWorkflowCommentStore("wf-unlaid").comments;
        expect(frame?.position).toEqual([0, 0]);
        expect(frame?.child_steps).toEqual([0, 1]);
    });

    it("keeps a partial layout and parks only the step without a position", async () => {
        await fromSimple("wf-mixed", workflow([0]));
        expect(useWorkflowStateStore("wf-mixed").needsInitialLayout).toBe(false);
        expect(useWorkflowStepStore("wf-mixed").steps[0]?.position).toEqual({ left: 0, top: 0 });
        expect(useWorkflowStepStore("wf-mixed").steps[1]?.position).toEqual({ left: 200, top: 100 });
    });

    it("does not lay out an empty workflow", async () => {
        await fromSimple("wf-empty", workflow([], []));
        expect(useWorkflowStateStore("wf-empty").needsInitialLayout).toBe(false);
    });

    it("leaves laid out workflows alone", async () => {
        await fromSimple("wf-laid", workflow([]));
        expect(useWorkflowStateStore("wf-laid").needsInitialLayout).toBe(false);
        expect(useWorkflowStepStore("wf-laid").steps[1]?.position).toEqual({ left: 200, top: 100 });
    });
});

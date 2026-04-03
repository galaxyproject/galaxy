import { createTestingPinia } from "@pinia/testing";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";

import { useInvocationGraph } from "./useInvocationGraph";

vi.mock("@/stores/workflowStore", () => ({
    useWorkflowStore: () => ({
        getFullWorkflowCached: vi.fn().mockResolvedValue({
            steps: { 0: { id: 0, type: "tool", position: { left: 0, top: 0 } } },
        }),
    }),
}));
vi.mock("@/components/Workflow/Editor/modules/model", () => ({ fromSimple: vi.fn() }));
vi.mock("./workflowStores", () => ({ provideScopedWorkflowStores: vi.fn() }));

/** Sets up the invocation graph composable for testing.
 * Initializes the composable and then loads it via its `loadInvocationGraph` function.
 */
function setupComposable(invStep?: object, summaries: object[] = []) {
    const invocation = ref({
        id: "inv1",
        steps: invStep ? { 0: invStep } : {},
        inputs: {},
        input_step_parameters: {},
    } as WorkflowInvocationElementView);
    const { steps, loadInvocationGraph } = useInvocationGraph(
        invocation,
        ref(summaries as StepJobSummary[]),
        ref("wf1"),
        ref(0),
    );
    return { steps, load: () => loadInvocationGraph(false) };
}

/** Helper function to set up a a version of the composable with provided job states */
function withJobStates(states: Record<string, number>, populated_state = "ok") {
    return setupComposable({ job_id: "j1" }, [{ id: "j1", model: "Job", states, populated_state }]);
}

describe("useInvocationGraph — step state", () => {
    beforeEach(() => {
        setActivePinia(createTestingPinia({ createSpy: vi.fn }));
    });

    it("is queued — no invocation step for this workflow step", async () => {
        const { steps, load } = setupComposable();
        await load();
        expect(steps.value[0]?.state).toBe("queued");
    });

    it("is waiting — invocation step present but no matching job summary", async () => {
        const { steps, load } = setupComposable({ job_id: "j1" });
        await load();
        expect(steps.value[0]?.state).toBe("waiting");
    });

    describe("from job states (single-instance: any one job triggers it)", () => {
        it("is error", async () => {
            const { steps, load } = withJobStates({ error: 1 });
            await load();
            expect(steps.value[0]?.state).toBe("error");
        });

        it("is running", async () => {
            const { steps, load } = withJobStates({ running: 1 });
            await load();
            expect(steps.value[0]?.state).toBe("running");
        });

        it("is paused", async () => {
            const { steps, load } = withJobStates({ paused: 1 });
            await load();
            expect(steps.value[0]?.state).toBe("paused");
        });

        it("is deleted — from deleting job state", async () => {
            const { steps, load } = withJobStates({ deleting: 1 });
            await load();
            expect(steps.value[0]?.state).toBe("deleted");
        });
    });

    describe("from job states (all-instances: all jobs must be in that state)", () => {
        it("is deleted", async () => {
            const { steps, load } = withJobStates({ deleted: 1 });
            await load();
            expect(steps.value[0]?.state).toBe("deleted");
        });

        it("is skipped", async () => {
            const { steps, load } = withJobStates({ skipped: 1 });
            await load();
            expect(steps.value[0]?.state).toBe("skipped");
        });

        it("is new", async () => {
            const { steps, load } = withJobStates({ new: 1 });
            await load();
            expect(steps.value[0]?.state).toBe("new");
        });

        it("is queued", async () => {
            const { steps, load } = withJobStates({ queued: 1 });
            await load();
            expect(steps.value[0]?.state).toBe("queued");
        });
    });

    describe("from populated_state fallback (when job states are inconclusive)", () => {
        // use { ok: 1 } — not in any SINGLE or ALL_INSTANCES list, so falls through to populated_state
        it("is queued — from scheduled populated_state", async () => {
            const { steps, load } = withJobStates({ ok: 1 }, "scheduled");
            await load();
            expect(steps.value[0]?.state).toBe("queued");
        });

        it("is queued — from ready populated_state", async () => {
            const { steps, load } = withJobStates({ ok: 1 }, "ready");
            await load();
            expect(steps.value[0]?.state).toBe("queued");
        });

        it("is new — from resubmitted populated_state", async () => {
            const { steps, load } = withJobStates({ ok: 1 }, "resubmitted");
            await load();
            expect(steps.value[0]?.state).toBe("new");
        });

        it("is error — from failed populated_state", async () => {
            const { steps, load } = withJobStates({ ok: 1 }, "failed");
            await load();
            expect(steps.value[0]?.state).toBe("error");
        });

        it("is deleted — from deleting populated_state", async () => {
            const { steps, load } = withJobStates({ ok: 1 }, "deleting");
            await load();
            expect(steps.value[0]?.state).toBe("deleted");
        });
    });
});

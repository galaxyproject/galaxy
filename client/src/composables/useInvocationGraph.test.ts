import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { InvocationStep, StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";

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

// The graph also accepts scheduling states omitted from the generated job-summary enum.
type PopulatedState = StepJobSummary["populated_state"] | "scheduled" | "ready";

function setupGraph({
    hasInvocationStep = true,
    states,
    populatedState = "ok",
}: {
    hasInvocationStep?: boolean;
    states?: StepJobSummary["states"];
    populatedState?: PopulatedState;
} = {}) {
    const invocationStep: InvocationStep = {
        id: "step-1",
        job_id: "j1",
        action: null,
        jobs: [],
        model_class: "WorkflowInvocationStep",
        order_index: 0,
        output_collections: {},
        outputs: {},
        update_time: null,
        workflow_step_id: "workflow-step-1",
    };
    const invocation = ref<WorkflowInvocationElementView>({
        id: "inv1",
        create_time: "2026-01-01T00:00:00",
        update_time: "2026-01-01T00:00:00",
        history_id: "history-1",
        workflow_id: "wf1",
        model_class: "WorkflowInvocation",
        state: "scheduled",
        steps: hasInvocationStep ? [invocationStep] : [],
        inputs: {},
        input_step_parameters: {},
        messages: [],
        output_collections: {},
        output_values: {},
        outputs: {},
    });
    const summaries = ref<StepJobSummary[]>(
        states
            ? [{ id: "j1", model: "Job", states, populated_state: populatedState as StepJobSummary["populated_state"] }]
            : [],
    );
    const { steps, loadInvocationGraph } = useInvocationGraph(invocation, summaries, ref("wf1"), ref(0));
    return { steps, load: () => loadInvocationGraph(false) };
}

describe("useInvocationGraph — step state", () => {
    it("is queued when this workflow step has no invocation step", async () => {
        const { steps, load } = setupGraph({ hasInvocationStep: false });
        await load();
        expect(steps.value[0]?.state).toBe("queued");
    });

    it("is waiting when the invocation step has no matching job summary", async () => {
        const { steps, load } = setupGraph();
        await load();
        expect(steps.value[0]?.state).toBe("waiting");
    });

    describe("when any job has a decisive state", () => {
        it.each([
            { jobState: "error", expectedState: "error" },
            { jobState: "running", expectedState: "running" },
            { jobState: "paused", expectedState: "paused" },
            { jobState: "deleting", expectedState: "deleted" },
        ])("maps $jobState to $expectedState", async ({ jobState, expectedState }) => {
            const { steps, load } = setupGraph({ states: { [jobState]: 1 } });
            await load();
            expect(steps.value[0]?.state).toBe(expectedState);
        });
    });

    describe("when all jobs are in the same state", () => {
        it.each(["deleted", "skipped", "new", "queued"])("preserves %s", async (jobState) => {
            const { steps, load } = setupGraph({ states: { [jobState]: 1 } });
            await load();
            expect(steps.value[0]?.state).toBe(jobState);
        });
    });

    it("assigns a header class to a fresh step", async () => {
        const { steps, load } = setupGraph({ hasInvocationStep: false });
        await load();
        expect(steps.value[0]?.headerClass).toBeDefined();
    });

    it("preserves uninitialized when job states are inconclusive and populated state is excluded", async () => {
        const { steps, load } = setupGraph({ states: { ok: 1 }, populatedState: "stop" });
        await load();
        expect(steps.value[0]?.state).toBe("uninitialized");
    });

    describe("populated state fallback when job states are inconclusive", () => {
        it.each<{
            populatedState: PopulatedState;
            expectedState: string;
        }>([
            { populatedState: "scheduled", expectedState: "queued" },
            { populatedState: "ready", expectedState: "queued" },
            { populatedState: "resubmitted", expectedState: "new" },
            { populatedState: "failed", expectedState: "error" },
            { populatedState: "deleting", expectedState: "deleted" },
        ])("maps $populatedState to $expectedState", async ({ populatedState, expectedState }) => {
            // An ok job state does not resolve the graph state, so populated_state decides it.
            const { steps, load } = setupGraph({ states: { ok: 1 }, populatedState });
            await load();
            expect(steps.value[0]?.state).toBe(expectedState);
        });
    });
});

import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref, watch } from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { InvocationStep, StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";

import { stepJobSummaryLookup, useInvocationGraph } from "./useInvocationGraph";

const toolStep = { id: 0, type: "tool", position: { left: 0, top: 0 } };
const workflowSteps = vi.hoisted(() => ({ value: {} as Record<number, object> }));

vi.mock("@/stores/workflowStore", () => ({
    useWorkflowStore: () => ({
        getFullWorkflowCached: vi.fn(async () => ({ steps: workflowSteps.value })),
    }),
}));
vi.mock("@/components/Workflow/Editor/modules/model", () => ({ fromSimple: vi.fn() }));
vi.mock("./workflowStores", () => ({ provideScopedWorkflowStores: vi.fn() }));

const { server, http } = useServerMock();

// The graph also accepts scheduling states omitted from the generated job-summary enum.
type PopulatedState = StepJobSummary["populated_state"] | "scheduled" | "ready";

function jobSummary(states: StepJobSummary["states"], populatedState: PopulatedState = "ok"): StepJobSummary {
    return { id: "j1", model: "Job", states, populated_state: populatedState as StepJobSummary["populated_state"] };
}

function setupGraph({
    hasInvocationStep = true,
    invocationStep: invocationStepOverrides = {},
    states,
    populatedState = "ok",
    inputStepParameters = {},
    invocationFields = {},
    loadOntoEditor = false,
}: {
    hasInvocationStep?: boolean;
    invocationStep?: Partial<InvocationStep>;
    states?: StepJobSummary["states"];
    populatedState?: PopulatedState;
    inputStepParameters?: WorkflowInvocationElementView["input_step_parameters"];
    invocationFields?: Partial<WorkflowInvocationElementView>;
    loadOntoEditor?: boolean;
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
        ...invocationStepOverrides,
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
        input_step_parameters: inputStepParameters,
        messages: [],
        output_collections: {},
        output_values: {},
        outputs: {},
        ...invocationFields,
    });
    const stepsJobsSummary = ref<StepJobSummary[]>(states ? [jobSummary(states, populatedState)] : []);
    const { steps, loadInvocationGraph } = useInvocationGraph(invocation, stepsJobsSummary, ref("wf1"), ref(0));
    return { steps, invocation, stepsJobsSummary, load: () => loadInvocationGraph(loadOntoEditor) };
}

/** A workflow with a dataset input feeding a tool, and an invocation of it that has been scheduled */
const inputAndToolSteps = {
    0: { id: 0, type: "data_input", position: { left: 0, top: 0 } },
    1: { ...toolStep, id: 1 },
};
const scheduledInputAndTool = {
    steps: [
        { id: "is0", workflow_step_id: 0 },
        { id: "is1", job_id: "j1" },
    ],
    inputs: { 0: { id: "d1", src: "hda" } },
} as unknown as Partial<WorkflowInvocationElementView>;
const inputDataset = { id: "d1", hid: 1, name: "input", state: "ok", history_content_type: "dataset" };

beforeEach(() => {
    workflowSteps.value = { 0: toolStep };
});

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

// The Overview graph loads onto the editor canvas, the Steps tab and Feedback don't; both must follow the polls.
describe.each([
    ["Steps tab", false],
    ["Overview graph", true],
])("useInvocationGraph — following polled data (%s)", (_name, loadOntoEditor) => {
    it("updates step states when a new jobs summary arrives", async () => {
        const { steps, stepsJobsSummary, load } = setupGraph({
            states: { queued: 1 },
            populatedState: "scheduled",
            loadOntoEditor,
        });
        await load();
        expect(steps.value[0]?.state).toBe("queued");

        stepsJobsSummary.value = [jobSummary({ running: 1 }, "scheduled")];
        await flushPromises();
        expect(steps.value[0]?.state).toBe("running");
        expect(steps.value[0]?.headerClass).toEqual({ "node-header-invocation": true, "header-running": true });

        stepsJobsSummary.value = [jobSummary({ ok: 1 })];
        await flushPromises();
        expect(steps.value[0]?.state).toBe("ok");
        expect(steps.value[0]?.jobs).toEqual({ ok: 1 });
    });

    it("updates step states when only the invocation changes", async () => {
        workflowSteps.value = { 0: { id: 0, type: "subworkflow", position: { left: 0, top: 0 } } };
        const { steps, invocation, load } = setupGraph({
            invocationStep: { id: "is0", job_id: null, state: "new" },
            loadOntoEditor,
        });
        await load();
        expect(steps.value[0]?.state).toBe("new");

        invocation.value = {
            ...invocation.value,
            steps: [{ ...invocation.value.steps[0]!, state: "failed" }],
        };
        await flushPromises();
        expect(steps.value[0]?.state).toBe("error");
    });

    it("updates a step once it is scheduled", async () => {
        const { steps, invocation, stepsJobsSummary, load } = setupGraph({ hasInvocationStep: false, loadOntoEditor });
        await load();
        expect(steps.value[0]?.state).toBe("queued");

        invocation.value = {
            ...invocation.value,
            steps: [{ id: "is0", job_id: "j1" }],
        } as WorkflowInvocationElementView;
        stepsJobsSummary.value = [jobSummary({ running: 1 }, "scheduled")];
        await flushPromises();
        expect(steps.value[0]?.state).toBe("running");
    });

    it("writes nothing to the steps when the polled data is unchanged", async () => {
        const { steps, invocation, stepsJobsSummary, load } = setupGraph({
            states: { running: 1 },
            populatedState: "scheduled",
            loadOntoEditor,
        });
        await load();
        let writes = 0;
        watch(steps, () => writes++, { deep: true, flush: "sync" });

        // A re-fetch with nothing changed yields equal copies, as the store produces on every poll.
        invocation.value = JSON.parse(JSON.stringify(invocation.value));
        stepsJobsSummary.value = JSON.parse(JSON.stringify(stepsJobsSummary.value));
        await flushPromises();
        // An explicit reload of unchanged data writes nothing either.
        await load();
        expect(writes).toBe(0);
    });

    it("keeps updating later steps when an input fetch fails, and retries the input", async () => {
        workflowSteps.value = inputAndToolSteps;
        const { steps, invocation, stepsJobsSummary, load } = setupGraph({ hasInvocationStep: false, loadOntoEditor });
        await load();
        server.use(
            http.get("/api/datasets/{dataset_id}", ({ response }) =>
                response("4XX").json({ err_code: 403002, err_msg: "Dataset is not accessible" }, { status: 403 }),
            ),
        );
        const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

        // Both steps appear once scheduled, but the input's dataset can't be fetched.
        invocation.value = { ...invocation.value, ...scheduledInputAndTool };
        stepsJobsSummary.value = [jobSummary({ running: 1 }, "scheduled")];
        await vi.waitFor(() =>
            expect(consoleError).toHaveBeenCalledWith("Failed to update invocation graph steps", expect.any(Error)),
        );
        expect(steps.value[1]?.state).toBe("running");
        expect(steps.value[0]?.nodeText).toBeUndefined();

        server.use(
            http.get("/api/datasets/{dataset_id}", ({ response }) => response.untyped(HttpResponse.json(inputDataset))),
        );
        stepsJobsSummary.value = [jobSummary({ ok: 1 })];
        await vi.waitFor(() => expect(steps.value[0]?.nodeText).toBe("1: <b>input</b>"));
        expect(steps.value[1]?.state).toBe("ok");
        consoleError.mockRestore();
    });

    it("applies a jobs summary that arrives while an input fetch is failing", async () => {
        workflowSteps.value = inputAndToolSteps;
        const { steps, invocation, stepsJobsSummary, load } = setupGraph({ hasInvocationStep: false, loadOntoEditor });
        await load();
        let datasetRequested = () => {};
        const requested = new Promise<void>((resolve) => (datasetRequested = resolve));
        let releaseDataset = () => {};
        const released = new Promise<void>((resolve) => (releaseDataset = resolve));
        server.use(
            http.get("/api/datasets/{dataset_id}", async ({ response }) => {
                datasetRequested();
                await released;
                return response("4XX").json(
                    { err_code: 403002, err_msg: "Dataset is not accessible" },
                    { status: 403 },
                );
            }),
        );
        const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

        invocation.value = { ...invocation.value, ...scheduledInputAndTool };
        stepsJobsSummary.value = [jobSummary({ running: 1 }, "scheduled")];
        await requested;
        // The last poll lands while the input fetch is still failing; no poll follows it.
        stepsJobsSummary.value = [jobSummary({ ok: 1 })];
        await flushPromises();
        releaseDataset();

        await vi.waitFor(() => expect(steps.value[1]?.state).toBe("ok"));
        expect(steps.value[0]?.nodeText).toBeUndefined();
        consoleError.mockRestore();
    });

    it("writes nothing to an input step without a value when the polled data is unchanged", async () => {
        workflowSteps.value = { 0: { id: 0, type: "data_input", position: { left: 0, top: 0 } } };
        const { steps, invocation, stepsJobsSummary, load } = setupGraph({
            invocationStep: { id: "is0", job_id: null, workflow_step_id: 0 } as unknown as Partial<InvocationStep>,
            loadOntoEditor,
        });
        await load();
        let writes = 0;
        watch(steps, () => writes++, { deep: true, flush: "sync" });

        invocation.value = JSON.parse(JSON.stringify(invocation.value));
        stepsJobsSummary.value = [];
        await flushPromises();
        expect(writes).toBe(0);
    });

    it("applies the latest jobs summary that arrives while an update is running", async () => {
        workflowSteps.value = inputAndToolSteps;
        let datasetRequested = () => {};
        const requested = new Promise<void>((resolve) => (datasetRequested = resolve));
        let releaseDataset = () => {};
        const released = new Promise<void>((resolve) => (releaseDataset = resolve));
        server.use(
            http.get("/api/datasets/{dataset_id}", async ({ response }) => {
                datasetRequested();
                await released;
                return response.untyped(HttpResponse.json(inputDataset));
            }),
        );
        const { steps, stepsJobsSummary, load } = setupGraph({
            states: { queued: 1 },
            populatedState: "scheduled",
            invocationFields: scheduledInputAndTool,
            loadOntoEditor,
        });

        // The first load waits on the input dataset while new polls land.
        const loaded = load();
        await requested;
        stepsJobsSummary.value = [jobSummary({ running: 1 }, "scheduled")];
        await flushPromises();
        stepsJobsSummary.value = [jobSummary({ ok: 1 })];
        await flushPromises();
        releaseDataset();
        await loaded;
        await flushPromises();

        expect(steps.value[0]?.state).toBe("ok");
        expect(steps.value[1]?.state).toBe("ok");
        expect(steps.value[1]?.jobs).toEqual({ ok: 1 });
    });
});

describe("stepJobSummaryLookup", () => {
    const jobStep = { job_id: "x1", implicit_collection_jobs_id: null } as InvocationStep;
    const collectionStep = { job_id: null, implicit_collection_jobs_id: "x1" } as InvocationStep;
    const lookup = stepJobSummaryLookup([
        { id: "x1", model: "Job", states: { ok: 1 }, populated_state: "ok" },
        { id: "x1", model: "ImplicitCollectionJobs", states: { error: 2 }, populated_state: "ok" },
    ] as StepJobSummary[]);

    it("matches a step's job by job id", () => {
        expect(lookup(jobStep)?.model).toBe("Job");
    });

    it("matches a mapped-over step by implicit collection jobs id", () => {
        expect(lookup(collectionStep)?.model).toBe("ImplicitCollectionJobs");
    });

    it("finds nothing for a step without jobs", () => {
        expect(lookup({ job_id: null, implicit_collection_jobs_id: null } as InvocationStep)).toBeUndefined();
    });
});

describe("useInvocationGraph — parameter input text", () => {
    async function loadParameterInput(parameterType: string, parameterValue: string) {
        const output = { name: "output", type: parameterType, optional: false, multiple: false, parameter: true };
        workflowSteps.value = {
            0: { id: 0, type: "parameter_input", position: { left: 0, top: 0 }, outputs: [output] },
        };
        const { steps, load } = setupGraph({
            inputStepParameters: {
                param: { label: "param", parameter_value: parameterValue, workflow_step_id: "workflow-step-1" },
            },
        });
        await load();
        return steps.value[0]?.nodeText;
    }

    it("passes a color parameter's raw hex through so the node renders a swatch", async () => {
        expect(await loadParameterInput("color", "#ff0000")).toBe("#ff0000");
    });

    it("bolds a text parameter even when its value looks like a color", async () => {
        expect(await loadParameterInput("text", "#ff0000")).toBe("<b>#ff0000</b>");
    });
});

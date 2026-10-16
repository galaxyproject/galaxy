import { createTestingPinia } from "@pinia/testing";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
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

/** Sets up the invocation graph composable for testing.
 * Initializes the composable and then loads it via its `loadInvocationGraph` function.
 */
function setupComposable(invStep?: object, summaries: object[] = [], loadOntoEditor = false, invocationFields = {}) {
    const invocation = ref({
        id: "inv1",
        steps: invStep ? { 0: invStep } : {},
        inputs: {},
        input_step_parameters: {},
        ...invocationFields,
    } as WorkflowInvocationElementView);
    const stepsJobsSummary = ref(summaries as StepJobSummary[]);
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
};
const inputDataset = { id: "d1", hid: 1, name: "input", state: "ok", history_content_type: "dataset" };

function jobSummary(states: Record<string, number>, populated_state = "ok", id = "j1") {
    return { id, model: "Job", states, populated_state } as StepJobSummary;
}

/** Helper function to set up a a version of the composable with provided job states */
function withJobStates(states: Record<string, number>, populated_state = "ok") {
    return setupComposable({ job_id: "j1" }, [jobSummary(states, populated_state)]);
}

beforeEach(() => {
    setActivePinia(createTestingPinia({ createSpy: vi.fn }));
    workflowSteps.value = { 0: toolStep };
});

describe("useInvocationGraph — step state", () => {
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

    describe("uninitialized state", () => {
        it("headerClass is set on a fresh step before state is determined", async () => {
            const { steps, load } = setupComposable();
            await load();
            expect(steps.value[0]?.headerClass).toBeDefined();
        });

        it("stays uninitialized when job states are inconclusive and populated_state is excluded", async () => {
            // "ok" not in SINGLE/ALL lists → getStepStateFromJobStates returns undefined
            // "stop" is explicitly excluded from the populated_state fallback
            // → newState stays undefined → preserves previous "uninitialized" state
            const { steps, load } = withJobStates({ ok: 1 }, "stop");
            await load();
            expect(steps.value[0]?.state).toBe("uninitialized");
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

// The Overview graph loads onto the editor canvas, the Steps tab and Feedback don't; both must follow the polls.
describe.each([
    ["Steps tab", false],
    ["Overview graph", true],
])("useInvocationGraph — following polled data (%s)", (_name, loadOntoEditor) => {
    it("updates step states when a new jobs summary arrives", async () => {
        const { steps, stepsJobsSummary, load } = setupComposable(
            { job_id: "j1" },
            [jobSummary({ queued: 1 }, "scheduled")],
            loadOntoEditor,
        );
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
        const { steps, invocation, load } = setupComposable({ id: "is0", state: "new" }, [], loadOntoEditor);
        await load();
        expect(steps.value[0]?.state).toBe("new");

        invocation.value = {
            ...invocation.value,
            steps: [{ id: "is0", state: "failed" }],
        } as WorkflowInvocationElementView;
        await flushPromises();
        expect(steps.value[0]?.state).toBe("error");
    });

    it("updates a step once it is scheduled", async () => {
        const { steps, invocation, stepsJobsSummary, load } = setupComposable(undefined, [], loadOntoEditor);
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
        const { steps, invocation, stepsJobsSummary, load } = setupComposable(
            { job_id: "j1" },
            [jobSummary({ running: 1 }, "scheduled")],
            loadOntoEditor,
        );
        await load();
        let writes = 0;
        watch(steps, () => writes++, { deep: true, flush: "sync" });

        // a re-fetch with nothing changed: equal copies, as the store produces on every poll
        invocation.value = JSON.parse(JSON.stringify(invocation.value));
        stepsJobsSummary.value = JSON.parse(JSON.stringify(stepsJobsSummary.value));
        await flushPromises();
        // an explicit reload of unchanged data writes nothing either
        await load();
        expect(writes).toBe(0);
    });

    it("keeps updating later steps when an input fetch fails, and retries the input", async () => {
        workflowSteps.value = inputAndToolSteps;
        const { steps, invocation, stepsJobsSummary, load } = setupComposable(undefined, [], loadOntoEditor);
        await load();
        server.use(
            http.get("/api/datasets/{dataset_id}", ({ response }) =>
                response("4XX").json({ err_code: 403002, err_msg: "Dataset is not accessible" }, { status: 403 }),
            ),
        );
        const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

        // the invocation is scheduled: both steps appear, but the input's dataset can't be fetched
        invocation.value = {
            ...invocation.value,
            ...scheduledInputAndTool,
        } as unknown as WorkflowInvocationElementView;
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
        const { steps, invocation, stepsJobsSummary, load } = setupComposable(undefined, [], loadOntoEditor);
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

        invocation.value = {
            ...invocation.value,
            ...scheduledInputAndTool,
        } as unknown as WorkflowInvocationElementView;
        stepsJobsSummary.value = [jobSummary({ running: 1 }, "scheduled")];
        await requested;
        // the last poll lands while the input fetch is still on its way to failing; no poll follows it
        stepsJobsSummary.value = [jobSummary({ ok: 1 })];
        await flushPromises();
        releaseDataset();

        await vi.waitFor(() => expect(steps.value[1]?.state).toBe("ok"));
        expect(steps.value[0]?.nodeText).toBeUndefined();
        consoleError.mockRestore();
    });

    it("writes nothing to an input step without a value when the polled data is unchanged", async () => {
        workflowSteps.value = { 0: { id: 0, type: "data_input", position: { left: 0, top: 0 } } };
        const { steps, invocation, stepsJobsSummary, load } = setupComposable(
            { id: "is0", workflow_step_id: 0 },
            [],
            loadOntoEditor,
        );
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
        const { steps, stepsJobsSummary, load } = setupComposable(
            undefined,
            [jobSummary({ queued: 1 }, "scheduled")],
            loadOntoEditor,
            scheduledInputAndTool,
        );

        // the first load waits on the input dataset while new polls land
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
    beforeEach(() => {
        setActivePinia(createTestingPinia({ createSpy: vi.fn }));
    });

    async function loadParameterInput(parameterType: string, parameterValue: string) {
        const output = { name: "output", type: parameterType, optional: false, multiple: false, parameter: true };
        workflowSteps.value = {
            0: { id: 0, type: "parameter_input", position: { left: 0, top: 0 }, outputs: [output] },
        };
        const { steps, invocation, load } = setupComposable({ workflow_step_id: 10 });
        invocation.value.input_step_parameters = {
            param: { label: "param", parameter_value: parameterValue, workflow_step_id: 10 },
        };
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

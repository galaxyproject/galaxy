import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http, HttpResponse } from "msw";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, ref } from "vue";
import { createMemoryHistory, createRouter, type LocationQuery, type Router } from "vue-router";

import { useServerMock } from "@/api/client/__mocks__";
import type { WorkflowInvocationElementView } from "@/api/invocations";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import { provideInvocationSelection, resolveStep, selectionQuery, useInvocationSelection } from "./invocationSelection";

const { server } = useServerMock();
const steps = [{ id: 0, label: "input" }, { id: 6, label: "trim reads" }, { id: 9 }, { id: 11, label: "7" }];
const fullWorkflow = { steps: Object.fromEntries(steps.map((step) => [step.id, step])) };

describe("invocation selection query", () => {
    it.each([
        [{ step_index: "6" }, 6],
        [{ step_number: "7" }, 6],
        [{ step_label: "trim reads" }, 6],
        [{ step_label: "7" }, 11],
        [{ step_index: "0", step_number: "7", step_label: "trim reads" }, 0],
        [{ step_number: "7", step_label: "input" }, 6],
    ])("resolves %j to its order_index", (query, expected) => {
        expect(resolveStep(query as LocationQuery, steps)).toBe(expected);
    });
    const malformedQueries: LocationQuery[] = [
        { step_number: "0" },
        { step_index: "1" },
        { step_index: "1.5" },
        { step_index: "-1" },
        { step_index: "9007199254740993" },
        { step_number: ["7", "1"] },
        { step_label: "missing" },
        { step_index: "bad", step_label: "input" },
    ];
    it.each(malformedQueries)("ignores malformed or absent selectors %j", (query) => {
        expect(resolveStep(query, steps)).toBeNull();
    });
    it("requires a unique label and writes readable selectors while preserving unrelated query state", () => {
        const duplicates = [...steps, { id: 7, label: "trim reads" }];
        expect(resolveStep({ step_label: "trim reads" }, duplicates)).toBeNull();
        expect(
            selectionQuery({ step_index: "6", success: "true", id: "report" }, duplicates, {
                stepIndex: 6,
                stepTab: "jobs",
                job: "encoded-job",
            }),
        ).toEqual({ id: "report", step_number: "7", step_tab: "jobs", job: "encoded-job" });
        expect(selectionQuery({}, steps, { stepIndex: 6 })).toEqual({ step_label: "trim reads" });
        expect(selectionQuery({ job: "stale", step_tab: "config" }, steps, { stepIndex: null })).toEqual({});
    });
});

describe("routed invocation selection", () => {
    let router: Router;
    let pinia: ReturnType<typeof createPinia>;
    let state: ReturnType<typeof useWorkflowStateStore>;
    let workflow: ReturnType<typeof useWorkflowStore>;
    const path = "/workflows/invocations/run";
    beforeEach(async () => {
        server.use(http.get("*/api/workflows/stored/download", () => HttpResponse.json(fullWorkflow)));
        pinia = createPinia();
        setActivePinia(pinia);
        state = useWorkflowStateStore("invocation-run");
        workflow = useWorkflowStore();
        router = createRouter({
            history: createMemoryHistory(),
            routes: [{ path: "/:pathMatch(.*)*", component: defineComponent({ render: () => h("div") }) }],
        });
        await router.push(path);
        await router.isReady();
    });
    function loadWorkflow() {
        workflow.workflowsByInstanceId.wf = {
            id: "stored",
            version: 1,
            steps: Object.fromEntries(steps.map((step) => [step.id, { id: step.id, type: "tool" }])),
        } as StoredWorkflowDetailed;
    }
    async function settle() {
        await flushPromises();
        await flushPromises();
    }
    function mountSelection(enabled = true) {
        let selection: ReturnType<typeof useInvocationSelection>;
        let mounts = 0;
        const Child = defineComponent({
            setup() {
                selection = useInvocationSelection();
                mounts++;
                return () => h("div");
            },
        });
        const invocation = ref({
            id: "run",
            workflow_id: "wf",
            state: "scheduled",
            steps: steps
                .slice()
                .reverse()
                .map((step) => ({ order_index: step.id, workflow_step_label: step.label ?? null })),
        } as WorkflowInvocationElementView);
        const wrapper = mount(
            defineComponent({
                setup() {
                    provideInvocationSelection(invocation, enabled);
                    return () => h(Child);
                },
            }),
            { global: { plugins: [pinia, router] } },
        );
        return {
            wrapper,
            invocation,
            get selection() {
                return selection!;
            },
            get mounts() {
                return mounts;
            },
        };
    }
    const selectors: LocationQuery[] = [{ step_number: "7" }, { step_index: "6" }, { step_label: "trim reads" }];
    it.each(selectors)("restores %j after summary loading and follows changes without remounting", async (selector) => {
        await router.push({ path, query: { ...selector, step_tab: "config", success: "true" } });
        const replace = vi.spyOn(router, "replace");
        const view = mountSelection();
        await settle();
        expect(replace).not.toHaveBeenCalled();
        loadWorkflow();
        await settle();
        expect(view.selection.stepIndex.value).toBe(6);
        expect(view.selection.stepTab.value).toBe("config");
        expect(router.currentRoute.value.query).toEqual({ step_label: "trim reads", step_tab: "config" });
        await router.push({ path, query: { step_index: "0", job: "job1" } });
        await settle();
        expect(view.selection.stepIndex.value).toBe(0);
        expect(view.selection.job.value).toBe("job1");
        expect(view.selection.stepTab.value).toBe("jobs");
        view.selection.stepIndex.value = 9;
        view.selection.stepTab.value = "config";
        await settle();
        expect(router.currentRoute.value.query).toEqual({ step_number: "10", step_tab: "config" });
        expect(view.mounts).toBe(1);
        view.wrapper.unmount();
    });
    it("keeps workflow outputs and report notebook queries independent of the retained graph node", async () => {
        state.activeNodeId = 6;
        loadWorkflow();
        await router.push({ path: path + "/outputs", query: { output: "counts" } });
        const outputs = mountSelection();
        await settle();
        expect(outputs.selection.output.value).toBe("counts");
        expect(router.currentRoute.value.query).toEqual({ output: "counts" });
        outputs.wrapper.unmount();
        await router.push({ path: path + "/reports", query: { id: "notebook" } });
        const replace = vi.spyOn(router, "replace");
        const reports = mountSelection();
        await settle();
        expect(replace).not.toHaveBeenCalled();
        expect(router.currentRoute.value.query).toEqual({ id: "notebook" });
        reports.wrapper.unmount();
    });
    it("requires an explicit valid step for a job link", async () => {
        state.activeNodeId = 6;
        loadWorkflow();
        await router.push({ path, query: { job: "orphan" } });
        const view = mountSelection();
        await settle();
        expect(view.selection.job.value).toBeUndefined();
        expect(router.currentRoute.value.query).toEqual({ step_label: "trim reads" });
        view.wrapper.unmount();
    });
    it("restores a retained graph selection and keeps embedded views independent of routing", async () => {
        state.activeNodeId = 6;
        loadWorkflow();
        const replace = vi.spyOn(router, "replace");
        const embedded = mountSelection(false);
        await settle();
        expect(embedded.selection).toBeUndefined();
        expect(replace).not.toHaveBeenCalled();
        embedded.wrapper.unmount();
        const routed = mountSelection();
        await settle();
        expect(router.currentRoute.value.query).toEqual({ step_label: "trim reads" });
        routed.wrapper.unmount();
    });
    it("retains selectors until complete workflow labels load, independently of invocation scheduling", async () => {
        let release!: () => void;
        const responseReady = new Promise<void>((resolve) => (release = resolve));
        let requested = false;
        server.use(
            http.get("*/api/workflows/stored/download", async () => {
                requested = true;
                await responseReady;
                return HttpResponse.json(fullWorkflow);
            }),
        );
        const query = { step_label: "trim reads", job: "late-job", output: "counts" };
        await router.push({ path, query });
        const view = mountSelection();
        view.invocation.value.state = "new";
        view.invocation.value.steps = [];
        loadWorkflow();
        await vi.waitFor(() => expect(requested).toBe(true));
        expect(router.currentRoute.value.query).toEqual(query);
        expect(view.selection.stepIndex.value).toBeNull();
        release();
        await vi.waitFor(() => expect(view.selection.stepIndex.value).toBe(6));
        expect(view.selection.job.value).toBe("late-job");
        expect(view.selection.output.value).toBe("counts");
        expect(router.currentRoute.value.query).toEqual({ ...query, step_tab: "jobs" });
        view.wrapper.unmount();
    });
    it("cleans an unknown label once complete workflow metadata is available", async () => {
        await router.push({ path, query: { step_label: "missing", job: "missing-job" } });
        const view = mountSelection();
        view.invocation.value.state = "new";
        loadWorkflow();
        await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({}));
        expect(view.selection.stepIndex.value).toBeNull();
        expect(view.selection.job.value).toBeUndefined();
        view.wrapper.unmount();
    });
    it("allows local choices to replace an unresolved invocation label before scheduling completes", async () => {
        await router.push({ path, query: { step_label: "pending", job: "old-job" } });
        const view = mountSelection();
        view.invocation.value.state = "new";
        view.invocation.value.steps = [];
        loadWorkflow();
        await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({}));
        view.selection.stepIndex.value = 0;
        await settle();
        expect(router.currentRoute.value.query).toEqual({ step_label: "input" });
        view.wrapper.unmount();
    });
    it("restores workflow output despite an irrelevant label without loading the full workflow", async () => {
        const fetch = vi.spyOn(workflow, "getFullWorkflowCached");
        await router.push({ path: path + "/outputs", query: { step_label: "pending", output: "counts" } });
        const view = mountSelection();
        view.invocation.value.state = "new";
        view.invocation.value.steps = [];
        loadWorkflow();
        await settle();
        expect(view.selection.output.value).toBe("counts");
        expect(router.currentRoute.value.query).toEqual({ output: "counts" });
        expect(fetch).not.toHaveBeenCalled();
        view.wrapper.unmount();
    });
    it("ignores a full workflow response after the invocation view is disposed", async () => {
        let release!: () => void;
        const responseReady = new Promise<void>((resolve) => (release = resolve));
        let requested = false;
        server.use(
            http.get("*/api/workflows/stored/download", async () => {
                requested = true;
                await responseReady;
                return HttpResponse.json(fullWorkflow);
            }),
        );
        await router.push({ path, query: { step_label: "trim reads" } });
        const view = mountSelection();
        loadWorkflow();
        await vi.waitFor(() => expect(requested).toBe(true));
        const replace = vi.spyOn(router, "replace");
        view.wrapper.unmount();
        release();
        await workflow.getFullWorkflowCached("stored", 1);
        await settle();
        expect(state.activeNodeId).toBeNull();
        expect(replace).not.toHaveBeenCalled();
    });
});

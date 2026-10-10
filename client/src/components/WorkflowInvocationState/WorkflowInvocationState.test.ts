import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type * as InvocationStoreModule from "@/stores/invocationStore";
import type * as WorkflowStoreModule from "@/stores/workflowStore";

import invocationData from "../Workflow/test/json/invocation.json";

import WorkflowInvocationOverview from "./WorkflowInvocationOverview.vue";
import WorkflowInvocationState from "./WorkflowInvocationState.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

const localVue = getLocalVue();

vi.mock("vue-router", async (importOriginal) => {
    const actual = (await importOriginal()) as Record<string, unknown>;
    return {
        ...actual,
        useRoute: vi.fn(() => ({})),
    };
});

const selectors = {
    debugTab: ".invocation-debug-tab",
    reportTab: ".invocation-report-tab",
    exportTab: ".invocation-export-tab",
};

const terminalJobsSummary = {
    model: "WorkflowInvocation",
    states: {},
    populated_state: "ok",
};

const storedInvocations: Record<string, unknown> = {};
const storedJobsSummaries: Record<string, unknown> = {};
const fetchInvocationById = vi.fn();
const fetchInvocationJobsSummaryForId = vi.fn();

vi.mock("@/stores/invocationStore", async () => {
    const originalModule = await vi.importActual<typeof InvocationStoreModule>("@/stores/invocationStore");
    return {
        ...originalModule,
        useInvocationStore: () => ({
            ...originalModule.useInvocationStore(),
            getInvocationById: (invocationId: string) => storedInvocations[invocationId],
            getInvocationJobsSummaryById: (invocationId: string) => storedJobsSummaries[invocationId],
            getInvocationStepJobsSummaryById: () => [
                { id: "job-id", model: "Job", populated_state: "ok", states: { ok: 1 } },
            ],
            fetchInvocationById,
            fetchInvocationJobsSummaryForId,
        }),
    };
});

vi.mock("@/stores/workflowStore", async () => {
    const originalModule = await vi.importActual<typeof WorkflowStoreModule>("@/stores/workflowStore");
    return {
        ...originalModule,
        useWorkflowStore: () => ({
            ...originalModule.useWorkflowStore(),
            getStoredWorkflowByInstanceId: () => ({ id: "workflow-id", name: "Test Workflow", version: 0 }),
        }),
    };
});

beforeEach(() => {
    for (const id of Object.keys(storedInvocations)) {
        delete storedInvocations[id];
        delete storedJobsSummaries[id];
    }
    fetchInvocationById.mockReset();
    fetchInvocationJobsSummaryForId.mockReset();
});

/** Puts a copy of the scheduled `invocationData` with `id` and `overrides`, plus its jobs summary, in the store */
function storeInvocation(id: string, jobsSummary: object, overrides: object = {}) {
    storedInvocations[id] = { ...invocationData, id, ...overrides };
    storedJobsSummaries[id] = jobsSummary;
}

async function mountWorkflowInvocationState(invocationId: string, { isFullPage = false } = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    const wrapper = shallowMount(WorkflowInvocationState as object, {
        props: { invocationId, isFullPage },
        pinia,
        global: localVue,
    });
    await flushPromises();
    return wrapper;
}

/** The terminal state the component reports to its overview */
function overviewTerminalState(wrapper: VueWrapper) {
    return wrapper.findComponent(WorkflowInvocationOverview).props("invocationAndJobTerminal");
}

describe("WorkflowInvocationState terminal state and polling", () => {
    it("reports a scheduled invocation with terminal jobs as terminal and fetches it once without its jobs summary", async () => {
        storeInvocation(invocationData.id, terminalJobsSummary);

        const wrapper = await mountWorkflowInvocationState(invocationData.id);

        expect(overviewTerminalState(wrapper)).toBe(true);
        expect(fetchInvocationById).toHaveBeenCalledTimes(1);
        expect(fetchInvocationById).toHaveBeenCalledWith({ id: invocationData.id });
        expect(fetchInvocationJobsSummaryForId).not.toHaveBeenCalled();
    });

    it("polls a new invocation once after the initial fetch without fetching its jobs summary", async () => {
        storeInvocation("non-terminal-id", terminalJobsSummary, { state: "new" });

        const wrapper = await mountWorkflowInvocationState("non-terminal-id");

        expect(overviewTerminalState(wrapper)).toBe(false);
        expect(fetchInvocationById).toHaveBeenCalledTimes(2);
        expect(fetchInvocationJobsSummaryForId).not.toHaveBeenCalled();
    });

    it("polls only the jobs summary of a scheduled invocation with a running job", async () => {
        storeInvocation("non-terminal-jobs", { ...terminalJobsSummary, states: { running: 1 } });

        const wrapper = await mountWorkflowInvocationState("non-terminal-jobs");

        expect(overviewTerminalState(wrapper)).toBe(false);
        expect(fetchInvocationById).toHaveBeenCalledTimes(1);
        expect(fetchInvocationJobsSummaryForId).toHaveBeenCalledTimes(1);
        expect(fetchInvocationJobsSummaryForId).toHaveBeenCalledWith({ id: "non-terminal-jobs" });
    });

    it("polls only the jobs summary of a scheduled invocation whose jobs are still being populated", async () => {
        storeInvocation("non-terminal-populated-state", { ...terminalJobsSummary, populated_state: "new" });

        const wrapper = await mountWorkflowInvocationState("non-terminal-populated-state");

        expect(overviewTerminalState(wrapper)).toBe(false);
        expect(fetchInvocationById).toHaveBeenCalledTimes(1);
        expect(fetchInvocationJobsSummaryForId).toHaveBeenCalledTimes(1);
    });

    it("shows an info alert and fetches no jobs summary when the fetched invocation is not in the store", async () => {
        storedInvocations["not-fetched-invocation"] = null;
        storedJobsSummaries["not-fetched-invocation"] = null;

        const wrapper = await mountWorkflowInvocationState("not-fetched-invocation");

        expect(wrapper.findComponent(WorkflowInvocationOverview).exists()).toBe(false);
        expect(fetchInvocationById).toHaveBeenCalledTimes(1);
        expect(fetchInvocationJobsSummaryForId).not.toHaveBeenCalled();
        const alert = wrapper.findComponent(GAlert);
        expect(alert.attributes("variant")).toBe("info");
        expect(alert.find("span").text()).toBe("Invocation not found.");
    });

    it("shows the error of a failed invocation fetch as a danger alert and fetches no jobs summary", async () => {
        fetchInvocationById.mockImplementation(() => {
            throw new Error("User does not own specified item.");
        });

        const wrapper = await mountWorkflowInvocationState("error-invocation");

        expect(wrapper.findComponent(WorkflowInvocationOverview).exists()).toBe(false);
        expect(fetchInvocationById).toHaveBeenCalledTimes(1);
        expect(fetchInvocationJobsSummaryForId).not.toHaveBeenCalled();
        const alert = wrapper.findComponent(GAlert);
        expect(alert.attributes("variant")).toBe("danger");
        expect(alert.text()).toBe("User does not own specified item.");
    });
});

describe("WorkflowInvocationState full page tabs", () => {
    it("disables the Report and Export tabs of a new invocation", async () => {
        storeInvocation("non-terminal-id", terminalJobsSummary, { state: "new" });

        const wrapper = await mountWorkflowInvocationState("non-terminal-id", { isFullPage: true });

        expect(wrapper.find(selectors.reportTab).attributes("disabled")).toBe("true");
        expect(wrapper.find(selectors.exportTab).attributes("disabled")).toBe("true");
    });

    it("enables the Report and Export tabs of a scheduled invocation with terminal jobs", async () => {
        storeInvocation(invocationData.id, terminalJobsSummary);

        const wrapper = await mountWorkflowInvocationState(invocationData.id, { isFullPage: true });

        expect(wrapper.find(selectors.reportTab).attributes("disabled")).toBeUndefined();
        expect(wrapper.find(selectors.exportTab).attributes("disabled")).toBeUndefined();
    });

    it("hides the Debug tab while an invocation with a failed job still has a running job", async () => {
        storeInvocation("non-terminal-error-jobs", { ...terminalJobsSummary, states: { running: 1, error: 1 } });

        const wrapper = await mountWorkflowInvocationState("non-terminal-error-jobs", { isFullPage: true });

        expect(overviewTerminalState(wrapper)).toBe(false);
        expect(wrapper.find(selectors.debugTab).exists()).toBe(false);
    });

    it("shows the Debug tab once an invocation with a failed job is terminal", async () => {
        storeInvocation("terminal-error-jobs", { ...terminalJobsSummary, states: { ok: 1, error: 1 } });

        const wrapper = await mountWorkflowInvocationState("terminal-error-jobs", { isFullPage: true });

        expect(overviewTerminalState(wrapper)).toBe(true);
        expect(wrapper.find(selectors.debugTab).exists()).toBe(true);
    });
});

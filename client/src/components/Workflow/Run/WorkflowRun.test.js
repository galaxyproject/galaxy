import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { resetMockConfig, setMockConfig } from "@/composables/__mocks__/config";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";

import { getRunData, WorkflowMissingToolsError } from "./services";
import sampleRunData1 from "./testdata/run1.json";

import WorkflowMissingToolsRequest from "./WorkflowMissingToolsRequest.vue";
import WorkflowRun from "./WorkflowRun.vue";
import WorkflowRunForm from "./WorkflowRunForm.vue";
import WorkflowRunFormSimple from "./WorkflowRunFormSimple.vue";

// Keep the real module (WorkflowMissingToolsError is matched with instanceof
// in the component) and only replace the API call. WorkflowRunModel rewrites the
// run data's inputs in place, so every load gets its own copy.
vi.mock("./services", async (importOriginal) => ({
    ...(await importOriginal()),
    getRunData: vi.fn(async () => structuredClone(sampleRunData1)),
}));

vi.mock("@/api/workflows", () => ({
    getWorkflowInfo: vi.fn(async () => ({
        id: "stored-workflow-id",
        name: "Missing Tools Workflow",
        owner: "someone",
    })),
}));

// WorkflowRunSuccess contains some bad code that automatically
// runs ajax calls, needs to be reworked and shallowMount doesn't
// seem to be stopping the event hooks from firing probably because the
// offending code runs immediately on loading
vi.mock("./WorkflowRunSuccess", () => ({
    default: {},
}));

vi.mock("@/composables/config");

const RUN1_WORKFLOW_ID = "ebab00128497f9d7";

const SELECTORS = {
    LOADING: "[data-description='loading message']",
    ERROR_ALERT: ".alert-danger",
    SUBMISSION_ERROR: "[data-description='workflow run error']",
    REQUEST_INSTALL_BUTTON: "[data-testid='request-install-btn']",
};

const REGISTERED_USER_STATE = {
    userStore: { currentUser: getFakeRegisteredUser() },
};

enableAutoUnmount(afterEach);

afterEach(() => {
    resetMockConfig();
});

function mountWorkflowRun(props = {}, initialState = {}) {
    return mount(WorkflowRun, {
        props: { workflowId: RUN1_WORKFLOW_ID, ...props },
        global: { plugins: [createTestingPinia({ createSpy: vi.fn, initialState })] },
    });
}

/** History polling re-runs loadRun through the historyStatusKey watcher. */
function triggerHistoryUpdate() {
    useHistoryItemsStore().lastUpdateTime = new Date(Date.now() + 1000);
}

describe("WorkflowRun", () => {
    it("loads run data from the API and passes the parsed model to the run form", async () => {
        const wrapper = mountWorkflowRun();
        expect(getRunData).toHaveBeenLastCalledWith(RUN1_WORKFLOW_ID, undefined, false);
        expect(wrapper.find(SELECTORS.LOADING).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.ERROR_ALERT).exists()).toBe(false);
        expect(wrapper.findComponent(WorkflowRunForm).exists()).toBe(false);

        await flushPromises();

        expect(wrapper.find(SELECTORS.LOADING).exists()).toBe(false);
        expect(wrapper.findComponent(WorkflowRunFormSimple).exists()).toBe(false);
        const workflowModel = wrapper.findComponent(WorkflowRunForm).props("model");
        expect(workflowModel.workflowId).toBe(RUN1_WORKFLOW_ID);
        expect(workflowModel.name).toBe("Cool Test Workflow");
        expect(workflowModel.historyId).toBe("8f7a155755f10e73");
        expect(workflowModel.hasUpgradeMessages).toBe(false);
        expect(workflowModel.hasStepVersionChanges).toBe(false);
        expect(workflowModel.wpInputs.wf_param.label).toBe("wf_param");
        // All five steps are expanded: data and parameter steps are expanded by default,
        // and so are tools with unconnected data inputs.
        expect(workflowModel.steps.map((step) => step.expanded)).toEqual([true, true, true, true, true]);
    });

    it("shows a submission error reported by the run form", async () => {
        const wrapper = mountWorkflowRun();
        await flushPromises();
        expect(wrapper.find(SELECTORS.ERROR_ALERT).exists()).toBe(false);

        wrapper.findComponent(WorkflowRunForm).vm.$emit("submissionError", "Some exception here");
        await nextTick();

        expect(wrapper.find(SELECTORS.SUBMISSION_ERROR).text()).toBe("Workflow submission failed: Some exception here");
        expect(wrapper.find(SELECTORS.ERROR_ALERT).exists()).toBe(true);
    });

    describe("missing tools", () => {
        const MISSING_TOOL_IDS = ["toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17"];
        const MISSING_TOOLS_MESSAGE = "Following tools missing: toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17";

        async function mountWithMissingTools(props = {}) {
            getRunData.mockRejectedValueOnce(new WorkflowMissingToolsError(MISSING_TOOLS_MESSAGE, MISSING_TOOL_IDS));
            const wrapper = mountWorkflowRun(props, REGISTERED_USER_STATE);
            await flushPromises();
            return wrapper;
        }

        beforeEach(() => {
            setMockConfig({ enable_notification_system: true, enable_tool_installation_request_form: true });
        });

        it("offers the install request for the tools reported missing", async () => {
            const wrapper = await mountWithMissingTools();

            expect(wrapper.find(SELECTORS.ERROR_ALERT).text()).toContain(MISSING_TOOLS_MESSAGE);
            const request = wrapper.findComponent(WorkflowMissingToolsRequest);
            expect(request.props("missingToolIds")).toEqual(MISSING_TOOL_IDS);
            // Non-instance run pages are addressed by the stored workflow id already.
            expect(request.props("workflowId")).toBe(RUN1_WORKFLOW_ID);
            expect(wrapper.find(SELECTORS.REQUEST_INSTALL_BUTTON).exists()).toBe(true);
        });

        it("resolves the stored workflow id for instance-mode run pages", async () => {
            const wrapper = await mountWithMissingTools({ instance: true });

            // `workflowId` is a Workflow instance id here; the request must carry the StoredWorkflow id.
            expect(wrapper.findComponent(WorkflowMissingToolsRequest).props("workflowId")).toBe("stored-workflow-id");
        });

        it("drops the missing tool ids when a reload fails for another reason", async () => {
            const wrapper = await mountWithMissingTools();
            expect(wrapper.find(SELECTORS.REQUEST_INSTALL_BUTTON).exists()).toBe(true);

            getRunData.mockRejectedValueOnce(new Error("Workflow cannot be run because it contains cycles."));
            triggerHistoryUpdate();
            await flushPromises();

            expect(wrapper.find(SELECTORS.ERROR_ALERT).text()).toContain(
                "Workflow cannot be run because it contains cycles.",
            );
            expect(wrapper.findComponent(WorkflowMissingToolsRequest).props("missingToolIds")).toEqual([]);
            expect(wrapper.find(SELECTORS.REQUEST_INSTALL_BUTTON).exists()).toBe(false);
        });

        it("clears the error state when a reload succeeds", async () => {
            const wrapper = await mountWithMissingTools();
            expect(wrapper.find(SELECTORS.ERROR_ALERT).text()).toContain(MISSING_TOOLS_MESSAGE);

            triggerHistoryUpdate();
            await flushPromises();

            expect(wrapper.find(SELECTORS.ERROR_ALERT).exists()).toBe(false);
            expect(wrapper.findComponent(WorkflowMissingToolsRequest).exists()).toBe(false);
            expect(wrapper.findComponent(WorkflowRunForm).props("model")).not.toBeNull();
        });
    });
});

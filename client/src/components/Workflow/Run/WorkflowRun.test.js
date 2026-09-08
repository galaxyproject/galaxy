import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setMockConfig } from "@/composables/__mocks__/config";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";

import { getRunData, WorkflowMissingToolsError } from "./services";
import sampleRunData1 from "./testdata/run1.json";

import WorkflowMissingToolsRequest from "./WorkflowMissingToolsRequest.vue";
import WorkflowRun from "./WorkflowRun.vue";

// Keep the real module (WorkflowMissingToolsError is matched with instanceof
// in the component) and only replace the API call.
vi.mock("./services", async (importOriginal) => ({
    ...(await importOriginal()),
    getRunData: vi.fn(async () => {
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve(sampleRunData1);
            }, 0);
        });
    }),
}));

vi.mock("@/api/workflows", () => ({
    getWorkflowInfo: vi.fn(async () => ({
        id: "stored-workflow-id",
        name: "Missing Tools Workflow",
        owner: "someone",
    })),
}));

vi.mock("app", () => ({}));

// WorkflowRunSuccess contains some bad code that automatically
// runs ajax calls, needs to be reworked and shallowMount doesn't
// seem to be stopping the event hooks from firing probably because the
// offending code runs immediately on loading
vi.mock("./WorkflowRunSuccess", () => ({
    default: {},
}));

vi.mock("@/composables/config");

describe("WorkflowRun.vue", () => {
    let wrapper;
    const run1WorkflowId = "ebab00128497f9d7";

    beforeEach(() => {
        vi.useFakeTimers();
        wrapper = mount(WorkflowRun, {
            props: {
                workflowId: run1WorkflowId,
            },
            global: {
                plugins: [createTestingPinia({ createSpy: vi.fn })],
            },
        });
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("loads run data from API and parses it into a WorkflowRunModel object", async () => {
        const loadingTag = "[data-description='loading message']";
        expect(wrapper.find(loadingTag).exists()).toBeTruthy();
        expect(wrapper.vm.workflowError).toBe("");
        expect(wrapper.vm.workflowModel).toBeNull();

        // Advance timers to trigger setTimeout
        await vi.runAllTimersAsync();
        await flushPromises();
        await wrapper.vm.$nextTick();

        expect(wrapper.find(loadingTag).exists()).toBeFalsy();
        expect(wrapper.vm.simpleForm).toBe(false);

        const workflowModel = wrapper.vm.workflowModel;
        expect(workflowModel).not.toBeNull();
        expect(workflowModel.workflowId).toBe(run1WorkflowId);
        expect(workflowModel.name).toBe("Cool Test Workflow");
        expect(workflowModel.historyId).toBe("8f7a155755f10e73");
        expect(workflowModel.hasUpgradeMessages).toBe(false);
        expect(workflowModel.hasStepVersionChanges).toBe(false);
        expect(workflowModel.wpInputs.wf_param.label).toBe("wf_param");
        // all steps are expanded since data and parameter steps are expanded by default,
        // the same is true for tools with unconnected data inputs.
        workflowModel.steps.forEach((step) => {
            expect(step.expanded).toBe(true);
        });
    });

    it("displays submission error", async () => {
        // waits for vue to render wrapper
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.loading).toBe(true);
        expect(wrapper.vm.workflowError).toBe("");
        expect(wrapper.vm.workflowModel).toBeNull();

        // Advance timers to trigger setTimeout
        await vi.runAllTimersAsync();
        await flushPromises();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.workflowError).toBe("");
        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.find(".alert-danger").exists()).toBe(false);
        wrapper.vm.handleSubmissionError("Some exception here");

        await wrapper.vm.$nextTick();

        expect(wrapper.vm.submissionError).toBe("Some exception here");
        expect(wrapper.find(".alert-danger").exists()).toBe(true);
    });

    describe("missing tools", () => {
        const MISSING_TOOL_IDS = ["toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17"];
        const MISSING_TOOLS_MESSAGE = "Following tools missing: toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17";

        function mountWithRegisteredUser(props = {}) {
            // @vue/test-utils v1: `propsData`, and the testing pinia becomes active on creation.
            createTestingPinia({
                createSpy: vi.fn,
                initialState: {
                    user: {
                        currentUser: { id: "user1", email: "u@galaxy.test", isAnonymous: false },
                    },
                },
            });
            return mount(WorkflowRun, {
                propsData: { workflowId: run1WorkflowId, ...props },
            });
        }

        async function settle(wrapper) {
            await vi.runAllTimersAsync();
            await flushPromises();
            await wrapper.vm.$nextTick();
        }

        beforeEach(() => {
            setMockConfig({ enable_tool_installation_request_form: true });
        });

        it("offers the install request for the tools reported missing", async () => {
            getRunData.mockRejectedValueOnce(new WorkflowMissingToolsError(MISSING_TOOLS_MESSAGE, MISSING_TOOL_IDS));
            const wrapper = mountWithRegisteredUser();
            await settle(wrapper);

            expect(wrapper.vm.workflowError).toBe(MISSING_TOOLS_MESSAGE);
            expect(wrapper.vm.missingToolIds).toEqual(MISSING_TOOL_IDS);
            const request = wrapper.findComponent(WorkflowMissingToolsRequest);
            expect(request.props("missingToolIds")).toEqual(MISSING_TOOL_IDS);
            // Non-instance run pages are addressed by the stored workflow id already.
            expect(request.props("workflowId")).toBe(run1WorkflowId);
            expect(wrapper.find("[data-testid='request-install-btn']").exists()).toBe(true);
        });

        it("resolves the stored workflow id for instance-mode run pages", async () => {
            getRunData.mockRejectedValueOnce(new WorkflowMissingToolsError(MISSING_TOOLS_MESSAGE, MISSING_TOOL_IDS));
            const wrapper = mountWithRegisteredUser({ instance: true });
            await settle(wrapper);

            // `workflowId` is a Workflow instance id here; the request must carry the StoredWorkflow id.
            expect(wrapper.findComponent(WorkflowMissingToolsRequest).props("workflowId")).toBe("stored-workflow-id");
        });

        it("drops the missing tool ids when a reload fails for another reason", async () => {
            getRunData.mockRejectedValueOnce(new WorkflowMissingToolsError(MISSING_TOOLS_MESSAGE, MISSING_TOOL_IDS));
            const wrapper = mountWithRegisteredUser();
            await settle(wrapper);
            expect(wrapper.find("[data-testid='request-install-btn']").exists()).toBe(true);

            getRunData.mockRejectedValueOnce(new Error("Workflow cannot be run because it contains cycles."));
            // History polling re-runs loadRun through the historyStatusKey watcher.
            useHistoryItemsStore().lastUpdateTime = new Date(Date.now() + 1000);
            await settle(wrapper);

            expect(wrapper.vm.workflowError).toBe("Workflow cannot be run because it contains cycles.");
            expect(wrapper.vm.missingToolIds).toEqual([]);
            expect(wrapper.findComponent(WorkflowMissingToolsRequest).props("missingToolIds")).toEqual([]);
            expect(wrapper.find("[data-testid='request-install-btn']").exists()).toBe(false);
        });

        it("clears the error state when a reload succeeds", async () => {
            getRunData.mockRejectedValueOnce(new WorkflowMissingToolsError(MISSING_TOOLS_MESSAGE, MISSING_TOOL_IDS));
            const wrapper = mountWithRegisteredUser();
            await settle(wrapper);
            expect(wrapper.vm.workflowError).toBe(MISSING_TOOLS_MESSAGE);

            useHistoryItemsStore().lastUpdateTime = new Date(Date.now() + 1000);
            await settle(wrapper);

            expect(wrapper.vm.workflowError).toBe("");
            expect(wrapper.vm.missingToolIds).toEqual([]);
            expect(wrapper.vm.workflowModel).not.toBeNull();
        });
    });
});

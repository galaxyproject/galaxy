import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, expect, it, vi } from "vitest";
import { ref } from "vue";

import WorkflowInvocationSteps from "./WorkflowInvocationSteps.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

const toolStep = { id: 0, type: "tool", tool_id: "cat1", annotation: "", input_steps: {}, inputs: [], outputs: [] };

const getFullWorkflowCached = vi.fn();

vi.mock("@/composables/useWorkflowInstance", () => ({
    useWorkflowInstance: () => ({
        workflow: ref({ id: "wf1", version: 0, steps: { 0: toolStep } }),
        loading: ref(false),
        error: ref(null),
    }),
}));
vi.mock("@/stores/workflowStore", () => ({
    useWorkflowStore: () => ({
        getFullWorkflowCached,
        getStoredWorkflowByInstanceId: vi.fn(),
    }),
}));
// Per-step polling is not under test: report no step details so nothing polls.
vi.mock("@/stores/invocationStore", () => ({
    useInvocationStore: () => ({
        getInvocationStepById: () => null,
        isLoadingInvocationStep: () => false,
        fetchInvocationStepById: vi.fn(),
    }),
}));
vi.mock("@/composables/datatypesMapper", () => ({ useDatatypesMapper: () => ({ datatypes: ref([]) }) }));
vi.mock("@/components/Workflow/Editor/modules/model", () => ({ fromSimple: vi.fn() }));
vi.mock("@/composables/workflowStores", () => ({ provideScopedWorkflowStores: vi.fn() }));

const invocation = {
    id: "inv1",
    workflow_id: "wf1",
    steps: [{ id: "is0", job_id: "j1", workflow_step_label: null, state: "scheduled" }],
    inputs: {},
    input_step_parameters: {},
};

function summary(states: Record<string, number>, populated_state: string) {
    return [{ id: "j1", model: "Job", states, populated_state }];
}

function mountSteps(): VueWrapper {
    return mount(WorkflowInvocationSteps as object, {
        propsData: { invocation, stepsJobsSummary: summary({ queued: 1 }, "scheduled") },
        localVue: getLocalVue(),
        pinia: createTestingPinia({ createSpy: vi.fn }),
        stubs: { DelayedInput: true, ToolLinkPopover: true, WorkflowStepIcon: true, WorkflowStepTitle: true },
    });
}

beforeEach(() => {
    getFullWorkflowCached.mockReset();
    getFullWorkflowCached.mockResolvedValue({ steps: { 0: toolStep } });
});

it("shows an error when the invocation graph fails to load", async () => {
    getFullWorkflowCached.mockRejectedValue(new Error("429 Too Many Requests"));
    const wrapper = mountSteps();
    await flushPromises();

    const alert = wrapper.findAllComponents(GAlert).filter((w) => w.props("variant") === "danger");
    expect(alert.at(0)!.text()).toContain("429 Too Many Requests");
});

it("step header follows the polled stepsJobsSummary prop", async () => {
    const wrapper = mountSteps();
    await flushPromises();
    const header = () => wrapper.find("[data-step='0'] .portlet-header");
    expect(header().classes()).toContain("header-queued");

    // expand the step: refreshes must not unmount the step list and collapse it
    await header().trigger("click");
    expect(wrapper.find("[data-step='0'] .portlet-content").exists()).toBe(true);

    // what WorkflowInvocationState's 3 s poll does: a new summary arrives as a new prop value
    await wrapper.setProps({ stepsJobsSummary: summary({ running: 1 }, "scheduled") });
    await flushPromises();
    expect(header().classes()).toContain("header-running");

    await wrapper.setProps({ stepsJobsSummary: summary({ ok: 1 }, "ok") });
    await flushPromises();
    expect(header().classes()).toContain("header-ok");
    expect(header().text()).toContain("successful");
    expect(wrapper.find("[data-step='0'] .portlet-content").exists()).toBe(true);
});

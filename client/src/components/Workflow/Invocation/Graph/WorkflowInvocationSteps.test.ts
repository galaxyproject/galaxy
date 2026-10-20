import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, shallowMount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, expect, it, vi } from "vitest";
import { ref } from "vue";

import WorkflowInvocationSteps from "./WorkflowInvocationSteps.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import WorkflowInvocationStep from "@/components/WorkflowInvocationState/WorkflowInvocationStep.vue";

const toolStep = { id: 0, type: "tool", tool_id: "cat1", annotation: "", input_steps: {}, inputs: [], outputs: [] };

const getFullWorkflowCached = vi.fn();
const mocks = vi.hoisted(() => ({ steps: {} as Record<number, unknown>, selection: undefined as any }));

vi.mock("@/composables/invocationSelection", () => ({ useInvocationSelection: () => mocks.selection }));
vi.mock("@/composables/useWorkflowInstance", () => ({
    useWorkflowInstance: () => ({
        workflow: ref({ id: "wf1", version: 0, steps: mocks.steps }),
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
    steps: [{ id: "is0", order_index: 0, job_id: "j1", workflow_step_label: null, state: "scheduled" }],
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

const localVue = getLocalVue();

beforeEach(() => {
    mocks.steps = { 0: toolStep };
    mocks.selection = undefined;
    getFullWorkflowCached.mockReset();
    getFullWorkflowCached.mockImplementation(async () => ({ steps: mocks.steps }));
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

it("expands the grouped input when a selection clears a previous search", async () => {
    mocks.steps = {
        0: { id: 0, type: "data_input", label: "reads" },
        1: { id: 1, type: "data_input", label: "reference" },
        2: { id: 2, type: "tool", label: "align" },
    };
    mocks.selection = { stepIndex: ref<number | null>(null), stepTab: ref(), job: ref(), output: ref() };
    // jsdom has no scrollIntoView; scrolling is covered by the browser test.
    Object.defineProperty(Element.prototype, "scrollIntoView", { configurable: true, value: () => {} });
    const wrapper = shallowMount(WorkflowInvocationSteps as object, {
        propsData: {
            invocation: { id: "inv1", workflow_id: "wf1", steps: [], inputs: {}, input_step_parameters: {} },
            stepsJobsSummary: [],
        },
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn }),
    });
    await flushPromises();
    wrapper.findComponent(DelayedInput).vm.$emit("change", "Step 3");
    await flushPromises();
    expect(wrapper.findAllComponents(WorkflowInvocationStep)).toHaveLength(1);
    mocks.selection.stepIndex.value = 0;
    await flushPromises();
    const inputs = wrapper.findAllComponents(WorkflowInvocationStep);
    expect(inputs).toHaveLength(3);
    expect(inputs.find((card) => card.props("workflowStep").id === 0)?.props("expanded")).toBe(true);
    wrapper.unmount();
});

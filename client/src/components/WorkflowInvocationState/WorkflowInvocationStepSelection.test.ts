import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http as mswHttp, HttpResponse } from "msw";
import { beforeEach, expect, it, vi } from "vitest";
import { reactive, ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { WorkflowInvocationElementView } from "@/api/invocations";
import type { WorkflowStepTyped } from "@/api/workflows";
import { type InvocationSelection, useInvocationSelection } from "@/composables/invocationSelection";

import WorkflowInvocationStep from "./WorkflowInvocationStep.vue";
import GenericItem from "@/components/History/Content/GenericItem.vue";

vi.mock("@/composables/invocationSelection", () => ({ useInvocationSelection: vi.fn() }));
vi.mock("@/composables/datatypesMapper", () => ({ useDatatypesMapper: () => ({ datatypes: [] }) }));
const { invocationStepDetails } = vi.hoisted(() => ({ invocationStepDetails: { value: undefined as any } }));
vi.mock("@/stores/invocationStore", () => ({
    useInvocationStore: () => ({
        getInvocationStepById: () =>
            invocationStepDetails.value ?? {
                state: "scheduled",
                jobs: [],
                output_collections: {},
                outputs: { first: { id: "first-id", src: "hda" }, second: { id: "second-id", src: "hda" } },
            },
        fetchInvocationStepById: vi.fn(),
    }),
}));

const { server } = useServerMock();
beforeEach(() => {
    invocationStepDetails.value = undefined;
    vi.clearAllMocks();
});
function mockConfigApi() {
    const requests: unknown[] = [];
    server.use(
        mswHttp.post("*/api/workflows/build_module", async ({ request }) => {
            requests.push(await request.json());
            return HttpResponse.json({ config_form: { inputs: [] } });
        }),
    );
    return requests;
}

it("keeps output selection scoped to the active card and follows same-mounted step changes", async () => {
    const selection: InvocationSelection = {
        stepIndex: ref(1),
        stepTab: ref("outputs"),
        job: ref(undefined),
        output: ref("first"),
    };
    vi.mocked(useInvocationSelection).mockReturnValue(selection);
    const invocation = {
        id: "invocation",
        inputs: {},
        input_step_parameters: {},
        steps: [
            { id: "step-1", order_index: 1 },
            { id: "step-2", order_index: 2 },
        ],
    } as WorkflowInvocationElementView;
    function mountStep(id: number) {
        return mount(WorkflowInvocationStep, {
            props: { invocation, workflowStep: { id, type: "tool" } as WorkflowStepTyped, expanded: true },
            global: {
                plugins: [createTestingPinia({ createSpy: vi.fn })],
                stubs: { GenericHistoryItem: true, WorkflowInvocationStepHeader: true },
            },
        });
    }
    const active = mountStep(1);
    const other = mountStep(2);
    await flushPromises();
    expect(active.findAllComponents(GenericItem).map((item) => item.props("expanded"))).toEqual([true, undefined]);
    expect(other.findAllComponents(GenericItem).map((item) => item.props("expanded"))).toEqual([undefined, undefined]);
    expect(selection.output.value).toBe("first");
    const secondOutput = other.findAllComponents(GenericItem)[1]!;
    secondOutput.vm.$emit("update:expanded", true);
    await flushPromises();
    expect(selection.stepIndex.value).toBe(2);
    expect(selection.output.value).toBe("second");
    expect(active.findAllComponents(GenericItem).every((item) => !item.props("expanded"))).toBe(true);
    expect(secondOutput.props("expanded")).toBe(true);
    other.findAllComponents(GenericItem)[0]!.vm.$emit("update:expanded", false);
    await flushPromises();
    expect(selection.output.value).toBe("second");
    selection.output.value = "first";
    await flushPromises();
    expect(other.findAllComponents(GenericItem)[0]!.props("expanded")).toBe(true);
    active.findAllComponents(GenericItem)[0]!.vm.$emit("update:expanded", false);
    await flushPromises();
    expect(selection.output.value).toBe("first");
    active.unmount();
    other.unmount();
});

it("opens a config URL immediately and follows later config and output tab changes", async () => {
    const selection: InvocationSelection = {
        stepIndex: ref(1),
        stepTab: ref("config"),
        job: ref(undefined),
        output: ref(undefined),
    };
    vi.mocked(useInvocationSelection).mockReturnValue(selection);
    const requests = mockConfigApi();
    const wrapper = mount(WorkflowInvocationStep, {
        props: {
            invocation: {
                id: "invocation",
                inputs: {},
                input_step_parameters: {},
                steps: [{ id: "step-1", order_index: 1 }],
            } as WorkflowInvocationElementView,
            workflowStep: { id: 1, type: "tool", tool_id: "cat" } as WorkflowStepTyped,
            expanded: true,
        },
        global: {
            plugins: [createTestingPinia({ createSpy: vi.fn })],
            stubs: { GenericHistoryItem: true, WorkflowInvocationStepHeader: true, FormTool: true },
        },
    });
    await flushPromises();
    expect(requests).toEqual([
        {
            type: "tool",
            content_id: "cat",
            tool_state: {},
        },
    ]);
    expect(wrapper.find("form-tool-stub").exists()).toBe(true);
    const selectedTab = () => wrapper.find('[role="tab"][aria-selected="true"]').text();
    expect(selectedTab()).toContain("Step Config");
    selection.stepTab.value = "outputs";
    await flushPromises();
    expect(selectedTab()).toBe("Outputs");
    selection.stepTab.value = "config";
    await flushPromises();
    expect(selectedTab()).toContain("Step Config");
    expect(requests).toHaveLength(1);
    const outputsTab = wrapper.findAll('[role="tab"]').find((tab) => tab.text() === "Outputs")!;
    await outputsTab.trigger("click");
    await flushPromises();
    expect(selection.stepTab.value).toBe("outputs");
    expect(selection.stepIndex.value).toBe(1);
    selection.stepTab.value = "config";
    await flushPromises();
    await wrapper.setProps({ expanded: false });
    expect(selection.stepTab.value).toBe("config");
    await wrapper.setProps({ expanded: true });
    await flushPromises();
    expect(selectedTab()).toContain("Step Config");
    selection.stepIndex.value = 2;
    selection.stepTab.value = "outputs";
    wrapper.unmount();
    expect(selection.stepIndex.value).toBe(2);
    expect(selection.stepTab.value).toBe("outputs");
});

it("preserves named tabs when a running step gains outputs", async () => {
    invocationStepDetails.value = reactive({ state: "scheduled", jobs: [], outputs: {}, output_collections: {} });
    const selection: InvocationSelection = {
        stepIndex: ref(1),
        stepTab: ref("config"),
        job: ref(undefined),
        output: ref(undefined),
    };
    vi.mocked(useInvocationSelection).mockReturnValue(selection);
    mockConfigApi();
    const wrapper = mount(WorkflowInvocationStep, {
        props: {
            invocation: {
                id: "invocation",
                inputs: {},
                input_step_parameters: {},
                steps: [{ id: "step-1", order_index: 1 }],
            } as WorkflowInvocationElementView,
            workflowStep: { id: 1, type: "tool" } as WorkflowStepTyped,
            expanded: true,
        },
        global: {
            plugins: [createTestingPinia({ createSpy: vi.fn })],
            stubs: { GenericHistoryItem: true, WorkflowInvocationStepHeader: true, FormTool: true },
        },
    });
    await flushPromises();
    const selectedTab = () => wrapper.find('[role="tab"][aria-selected="true"]').text();
    expect(selectedTab()).toContain("Step Config");
    invocationStepDetails.value.outputs = { first: { id: "first-id", src: "hda" } };
    await flushPromises();
    expect(selectedTab()).toContain("Step Config");
    expect(selection.stepTab.value).toBe("config");
    selection.stepTab.value = "outputs";
    await flushPromises();
    expect(selectedTab()).toBe("Outputs");
    wrapper.unmount();
    invocationStepDetails.value = undefined;
});

it("drops a tab, job or output link once the step is terminal and cannot show it", async () => {
    invocationStepDetails.value = reactive({
        state: "scheduled",
        jobs: [{ id: "job-1", state: "running" }],
        outputs: {},
        output_collections: {},
    });
    const selection: InvocationSelection = {
        stepIndex: ref(1),
        stepTab: ref("outputs"),
        job: ref("missing-job"),
        output: ref("missing-output"),
    };
    vi.mocked(useInvocationSelection).mockReturnValue(selection);
    const wrapper = mount(WorkflowInvocationStep, {
        props: {
            invocation: {
                id: "invocation",
                inputs: {},
                input_step_parameters: {},
                steps: [{ id: "step-1", order_index: 1 }],
            } as WorkflowInvocationElementView,
            workflowStep: { id: 1, type: "tool" } as WorkflowStepTyped,
            expanded: true,
        },
        global: {
            plugins: [createTestingPinia({ createSpy: vi.fn })],
            stubs: { GenericHistoryItem: true, WorkflowInvocationStepHeader: true, JobStep: true },
        },
    });
    await flushPromises();
    expect([selection.stepTab.value, selection.job.value, selection.output.value]).toEqual([
        "outputs",
        "missing-job",
        "missing-output",
    ]);
    invocationStepDetails.value.jobs[0].state = "ok";
    await flushPromises();
    expect([selection.stepTab.value, selection.job.value, selection.output.value]).toEqual([
        undefined,
        undefined,
        undefined,
    ]);
    selection.job.value = "job-1";
    await flushPromises();
    expect(selection.job.value).toBe("job-1");
    wrapper.unmount();
    invocationStepDetails.value = undefined;
});

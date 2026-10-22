import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, expect, it, vi } from "vitest";
import { ref } from "vue";

import InvocationGraph from "./InvocationGraph.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

const loadInvocationGraph = vi.fn();

vi.mock("@/composables/useInvocationGraph", () => ({
    useInvocationGraph: () => ({
        steps: ref({}),
        storeId: ref("invocation-inv1"),
        loading: ref(false),
        loadInvocationGraph,
    }),
}));
vi.mock("@/composables/datatypesMapper", () => ({ useDatatypesMapper: () => ({ datatypesMapper: ref({}) }) }));

beforeEach(() => {
    loadInvocationGraph.mockReset();
});

// The parent polls the invocation and the jobs summary separately; either may be the only one still polling
it.each([
    ["jobs summary", { stepsJobsSummary: [] }],
    ["invocation", { invocation: { id: "inv1", steps: [] } }],
])("retries a failed graph load when the parent polls a new %s", async (_name, polledProps) => {
    loadInvocationGraph.mockRejectedValueOnce(new Error("429 Too Many Requests")).mockResolvedValue(undefined);
    const wrapper: VueWrapper = shallowMount(InvocationGraph as object, {
        propsData: {
            invocation: { id: "inv1", steps: [] },
            stepsJobsSummary: [],
            workflow: { id: "wf1", version: 0, steps: {} },
        },
        localVue: getLocalVue(),
        pinia: createTestingPinia({ createSpy: vi.fn }),
    });
    await flushPromises();
    const errorAlert = () => wrapper.findAllComponents(GAlert).filter((w) => w.props("variant") === "danger");
    expect(errorAlert().at(0)!.text()).toContain("429 Too Many Requests");

    await wrapper.setProps(polledProps);
    await flushPromises();
    expect(errorAlert().length).toBe(0);
    expect(wrapper.findComponent(WorkflowGraph).exists()).toBe(true);
});

import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { expect, it, vi } from "vitest";
import { ref } from "vue";

import InvocationGraph from "./InvocationGraph.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

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

it("retries a failed graph load when the parent polls new data", async () => {
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

    await wrapper.setProps({ stepsJobsSummary: [] });
    await flushPromises();
    expect(loadInvocationGraph).toHaveBeenCalledTimes(2);
    expect(errorAlert().length).toBe(0);
});

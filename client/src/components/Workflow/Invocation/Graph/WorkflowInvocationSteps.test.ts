import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { expect, it, vi } from "vitest";
import { ref } from "vue";

import WorkflowInvocationSteps from "./WorkflowInvocationSteps.vue";

vi.mock("@/composables/useWorkflowInstance", () => ({
    useWorkflowInstance: () => ({
        workflow: ref({ id: "workflow_id", version: 0, steps: {} }),
        loading: ref(false),
        error: ref(null),
    }),
}));

vi.mock("@/composables/useInvocationGraph", () => ({
    useInvocationGraph: () => ({
        steps: ref({}),
        loading: ref(false),
        loadInvocationGraph: vi.fn().mockRejectedValue(new Error("429 Too Many Requests")),
    }),
}));

const localVue = getLocalVue();

it("shows an error when the invocation graph fails to load", async () => {
    const wrapper = shallowMount(WorkflowInvocationSteps as object, {
        propsData: {
            invocation: { id: "invocation_id", workflow_id: "workflow_id", steps: [] },
            stepsJobsSummary: [],
        },
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn }),
    });
    await flushPromises();

    expect(wrapper.find("balert-stub[variant='danger']").text()).toContain("429 Too Many Requests");
});

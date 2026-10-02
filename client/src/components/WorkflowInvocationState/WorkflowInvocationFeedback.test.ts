import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { expect, it, vi } from "vitest";
import { ref } from "vue";

import WorkflowInvocationFeedback from "./WorkflowInvocationFeedback.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

vi.mock("@/composables/useWorkflowInstance", () => ({
    useWorkflowInstance: () => ({
        workflow: ref({ id: "workflow_id", version: 0, steps: {} }),
        loading: ref(false),
        error: ref(null),
    }),
}));

vi.mock("@/composables/useInvocationGraph", () => ({
    useInvocationGraph: () => ({
        steps: ref(undefined),
        loading: ref(false),
        loadInvocationGraph: vi.fn().mockRejectedValue(new Error("429 Too Many Requests")),
    }),
}));

const localVue = getLocalVue();

it("shows a warning when the steps with errors fail to load", async () => {
    const wrapper = shallowMount(WorkflowInvocationFeedback as object, {
        propsData: {
            invocationId: "invocation_id",
            invocation: { id: "invocation_id", workflow_id: "workflow_id", steps: [] },
            stepsJobsSummary: [],
            invocationMessages: [],
        },
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn }),
    });
    await flushPromises();

    const alert = wrapper.findComponent(GAlert);
    expect(alert.props("variant")).toBe("warning");
    expect(alert.text()).toContain("429 Too Many Requests");
});

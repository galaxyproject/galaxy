import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { expect, it, vi } from "vitest";
import { ref } from "vue";

import type { WorkflowStepTyped } from "@/api/workflows";

import WorkflowInvocationFeedback from "./WorkflowInvocationFeedback.vue";
import WorkflowInvocationStep from "./WorkflowInvocationStep.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

vi.mock("@/composables/useWorkflowInstance", () => ({
    useWorkflowInstance: () => ({
        workflow: ref({ id: "workflow_id", version: 0, steps: {} }),
        loading: ref(false),
        error: ref(null),
    }),
}));

const mocks = vi.hoisted(() => ({
    steps: undefined as Record<number, Pick<WorkflowStepTyped, "id" | "type">> | undefined,
    load: vi.fn(),
}));
vi.mock("@/composables/useInvocationGraph", async () => ({
    ...(await vi.importActual("@/composables/useInvocationGraph")),
    useInvocationGraph: () => ({
        steps: ref(mocks.steps),
        loading: ref(false),
        loadInvocationGraph: mocks.load,
    }),
}));

const localVue = getLocalVue();

it("shows a warning when the steps with errors fail to load", async () => {
    mocks.load.mockRejectedValue(new Error("429 Too Many Requests"));
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

it("matches failed job summaries by workflow order when invocation steps arrive out of order", async () => {
    mocks.steps = { 0: { id: 0, type: "tool" }, 1: { id: 1, type: "tool" } };
    mocks.load.mockResolvedValue(undefined);
    const wrapper = shallowMount(WorkflowInvocationFeedback as object, {
        propsData: {
            invocationId: "inv1",
            invocation: {
                id: "inv1",
                workflow_id: "wf1",
                steps: [
                    { id: "is1", order_index: 1, job_id: "failed" },
                    { id: "is0", order_index: 0, job_id: "ok" },
                ],
            },
            stepsJobsSummary: [
                { id: "failed", model: "Job", states: { error: 1 }, populated_state: "ok" },
                { id: "ok", model: "Job", states: { ok: 1 }, populated_state: "ok" },
            ],
            invocationMessages: [],
        },
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn }),
    });
    await flushPromises();
    const cards = wrapper.findAllComponents(WorkflowInvocationStep);
    expect(cards).toHaveLength(1);
    expect(cards[0]!.props("workflowStep").id).toBe(1);
    wrapper.unmount();
});

import { createTestingPinia } from "@pinia/testing";
import { shallowMount, Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import type { WorkflowInvocation } from "@/api/invocations";

import invocationData from "../Workflow/test/json/invocation.json";

import WorkflowInvocationState from "./WorkflowInvocationState.vue";

const localVue = getLocalVue();

const selectors = {
    invocationSummary: ".invocation-summary",
};

const invocationJobsSummaryById = {
    id: "d9833097445452b0",
    model: "WorkflowInvocation",
    states: {},
    populated_state: "ok",
};

async function mountWorkflowInvocationState(invocation: WorkflowInvocation | null) {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    const wrapper = shallowMount(WorkflowInvocationState, {
        propsData: {
            invocationId: invocationData.id,
        },
        computed: {
            invocation: () => invocation,
            jobStatesSummary: () => invocationJobsSummaryById,
        },
        pinia,
        localVue,
    });
    await flushPromises();
    return wrapper;
}

describe("WorkflowInvocationState.vue", () => {
    it("determines that invocation and job states are terminal with terminal invocation", async () => {
        const wrapper = await mountWorkflowInvocationState(invocationData as WorkflowInvocation);
        expect(isInvocationAndJobTerminal(wrapper)).toBe(true);
    });

    it("determines that invocation and job states are not terminal with no invocation", async () => {
        const wrapper = await mountWorkflowInvocationState(null);
        expect(isInvocationAndJobTerminal(wrapper)).toBe(false);
    });

    it("determines that invocation and job states are not terminal with non-terminal invocation", async () => {
        const invocation = {
            ...invocationData,
            state: "new",
        } as WorkflowInvocation;
        const wrapper = await mountWorkflowInvocationState(invocation);
        expect(isInvocationAndJobTerminal(wrapper)).toBe(false);
    });
});

function isInvocationAndJobTerminal(wrapper: Wrapper<Vue>): boolean {
    const invocationSummary = wrapper.find(selectors.invocationSummary);
    // This is a somewhat hacky way to determine if the invocation and job states are terminal without
    // exposing the internals of the component. This is just to restore the previous behavior of the test
    // but it would be better to test this in a more appropriate way.
    return invocationSummary.exists() && invocationSummary.html().includes('invocationandjobterminal="true"');
}

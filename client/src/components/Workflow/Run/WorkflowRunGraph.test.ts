import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { getDatatypesMapper } from "@/components/Datatypes";

import WorkflowRunGraph from "./WorkflowRunGraph.vue";

vi.mock("@/components/Datatypes", () => ({
    getDatatypesMapper: vi.fn(),
}));

vi.mock("@/composables/useWorkflowRunGraph", () => ({
    useWorkflowRunGraph: vi.fn(() => ({
        steps: ref({}),
        loading: ref(false),
        loadWorkflowOntoGraph: vi.fn(),
    })),
}));

describe("WorkflowRunGraph", () => {
    it("shows an error when the datatypes fail to load", async () => {
        vi.mocked(getDatatypesMapper).mockRejectedValue(new Error("Datatypes unavailable"));
        const wrapper = mount(WorkflowRunGraph as object, {
            props: { workflowId: "workflow_id", storedId: "stored_id", version: 0, inputs: {}, formInputs: [] },
            global: { ...getLocalVue(), stubs: { WorkflowGraph: true } },
        });
        await flushPromises();
        expect(wrapper.find(".alert-danger").text()).toBe("Datatypes unavailable");
    });
});

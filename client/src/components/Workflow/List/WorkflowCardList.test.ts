import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import WorkflowCard from "./WorkflowCard.vue";
import WorkflowCardList from "./WorkflowCardList.vue";
import WorkflowRename from "@/components/Common/RenameModal.vue";

vi.mock("@/components/Workflow/workflows.services", () => ({
    updateWorkflow: vi.fn(),
}));

vi.mock("@/composables/toast", () => ({
    Toast: { success: vi.fn(), error: vi.fn() },
    useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const localVue = getLocalVue();

const WORKFLOW_ID = "workflow-abc123";
const WORKFLOW_NAME = "My Test Workflow";
const FAKE_WORKFLOW = { id: WORKFLOW_ID, name: WORKFLOW_NAME };

const WORKFLOW_2_ID = "workflow-def456";
const WORKFLOW_2_NAME = "Another Workflow";
const FAKE_WORKFLOW_2 = { id: WORKFLOW_2_ID, name: WORKFLOW_2_NAME };

describe("WorkflowCardList — rename flow", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("shows WorkflowRename with correct props when a card emits rename", async () => {
        const wrapper = shallowMount(WorkflowCardList as object, {
            localVue,
            propsData: { workflows: [FAKE_WORKFLOW] },
        });

        expect(wrapper.findComponent(WorkflowRename).exists()).toBe(false);

        wrapper.findComponent(WorkflowCard).vm.$emit("rename", WORKFLOW_ID, WORKFLOW_NAME);
        await flushPromises();

        const renameModal = wrapper.findComponent(WorkflowRename);
        expect(renameModal.exists()).toBe(true);
        expect(renameModal.props("name")).toBe(WORKFLOW_NAME);
    });

    it("does not retain first workflow's name when opening rename for a different workflow after aborting", async () => {
        const wrapper = shallowMount(WorkflowCardList as object, {
            localVue,
            propsData: { workflows: [FAKE_WORKFLOW, FAKE_WORKFLOW_2] },
        });

        // Open rename for first workflow then abort
        wrapper.findComponent(WorkflowCard).vm.$emit("rename", WORKFLOW_ID, WORKFLOW_NAME);
        await flushPromises();
        wrapper.findComponent(WorkflowRename).vm.$emit("close");
        await flushPromises();

        expect(wrapper.findComponent(WorkflowRename).exists()).toBe(false);

        // Open rename for second workflow
        wrapper.findComponent(WorkflowCard).vm.$emit("rename", WORKFLOW_2_ID, WORKFLOW_2_NAME);
        await flushPromises();

        const renameModal = wrapper.findComponent(WorkflowRename);
        expect(renameModal.props("name")).toBe(WORKFLOW_2_NAME);
    });
});

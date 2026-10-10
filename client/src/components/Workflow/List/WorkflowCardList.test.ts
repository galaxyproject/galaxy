import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { WorkflowSummary } from "@/api/workflows";
import { updateWorkflow } from "@/components/Workflow/workflows.services";

import WorkflowCard from "./WorkflowCard.vue";
import WorkflowCardList from "./WorkflowCardList.vue";
import WorkflowRename from "@/components/Common/RenameModal.vue";

vi.mock("@/components/Workflow/workflows.services", () => ({
    updateWorkflow: vi.fn(),
}));

vi.mock("@/composables/toast");

const localVue = getLocalVue();

const FIRST_WORKFLOW = getFakeWorkflowSummary({ id: "workflow-abc123", name: "My Test Workflow" });
const SECOND_WORKFLOW = getFakeWorkflowSummary({ id: "workflow-def456", name: "Another Workflow" });

function mountWorkflowCardList(workflows: WorkflowSummary[]) {
    return shallowMount(WorkflowCardList, {
        localVue,
        propsData: { workflows },
    });
}

type Wrapper = ReturnType<typeof mountWorkflowCardList>;

async function requestRename(wrapper: Wrapper, cardIndex: number, workflow: WorkflowSummary) {
    wrapper.findAllComponents(WorkflowCard).at(cardIndex)!.vm.$emit("rename", workflow.id, workflow.name);
    await flushPromises();
}

describe("WorkflowCardList — rename flow", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("shows WorkflowRename with correct props when a card emits rename", async () => {
        const wrapper = mountWorkflowCardList([FIRST_WORKFLOW]);

        expect(wrapper.findComponent(WorkflowRename).exists()).toBe(false);

        await requestRename(wrapper, 0, FIRST_WORKFLOW);

        const renameModal = wrapper.findComponent(WorkflowRename);
        expect(renameModal.exists()).toBe(true);
        expect(renameModal.props("name")).toBe(FIRST_WORKFLOW.name);
    });

    it("does not retain first workflow's name when opening rename for a different workflow after aborting", async () => {
        const wrapper = mountWorkflowCardList([FIRST_WORKFLOW, SECOND_WORKFLOW]);

        await requestRename(wrapper, 0, FIRST_WORKFLOW);
        wrapper.findComponent(WorkflowRename).vm.$emit("close");
        await flushPromises();

        expect(wrapper.findComponent(WorkflowRename).exists()).toBe(false);
        expect(wrapper.emitted("refreshList")).toEqual([[true, true]]);

        await requestRename(wrapper, 1, SECOND_WORKFLOW);

        const renameModal = wrapper.findComponent(WorkflowRename);
        expect(renameModal.props("name")).toBe(SECOND_WORKFLOW.name);

        await renameModal.props("renameAction")("Renamed Workflow");
        expect(updateWorkflow).toHaveBeenCalledWith(SECOND_WORKFLOW.id, { name: "Renamed Workflow" });
    });
});

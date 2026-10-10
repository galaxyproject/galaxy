import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { WorkflowSummary } from "@/api/workflows";
import { updateWorkflow } from "@/components/Workflow/workflows.services";

import * as WorkflowCardListStories from "./WorkflowCardList.stories";

import WorkflowCard from "./WorkflowCard.vue";
import WorkflowCardList from "./WorkflowCardList.vue";
import WorkflowRename from "@/components/Common/RenameModal.vue";

// Spied, not replaced: the rename still reaches the story's handler.
vi.mock("@/components/Workflow/workflows.services", { spy: true });

const stories = composeStories(WorkflowCardListStories);
const mountStory = useStoryMount();

const FIRST_WORKFLOW = stories.OwnWorkflows.args.workflows![0]!;
const SECOND_WORKFLOW = stories.OwnWorkflows.args.workflows![1]!;

async function mountWorkflowCardList() {
    const wrapper = mountStory(stories.OwnWorkflows);
    await flushPromises();
    return wrapper;
}

async function requestRename(wrapper: VueWrapper, cardIndex: number, workflow: WorkflowSummary) {
    wrapper.findAllComponents(WorkflowCard).at(cardIndex)!.vm.$emit("rename", workflow.id, workflow.name);
    await flushPromises();
}

describe("WorkflowCardList — rename flow", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("shows WorkflowRename with correct props when a card emits rename", async () => {
        const wrapper = await mountWorkflowCardList();

        expect(wrapper.findComponent(WorkflowRename).exists()).toBe(false);

        await requestRename(wrapper, 0, FIRST_WORKFLOW);

        const renameModal = wrapper.findComponent(WorkflowRename);
        expect(renameModal.exists()).toBe(true);
        expect(renameModal.props("name")).toBe(FIRST_WORKFLOW.name);
    });

    it("does not retain first workflow's name when opening rename for a different workflow after aborting", async () => {
        const wrapper = await mountWorkflowCardList();

        await requestRename(wrapper, 0, FIRST_WORKFLOW);
        wrapper.findComponent(WorkflowRename).vm.$emit("close");
        await flushPromises();

        expect(wrapper.findComponent(WorkflowRename).exists()).toBe(false);
        expect(wrapper.getComponent(WorkflowCardList).emitted("refreshList")).toEqual([[true, true]]);

        await requestRename(wrapper, 1, SECOND_WORKFLOW);

        const renameModal = wrapper.findComponent(WorkflowRename);
        expect(renameModal.props("name")).toBe(SECOND_WORKFLOW.name);

        await renameModal.props("renameAction")("Renamed Workflow");
        expect(updateWorkflow).toHaveBeenCalledWith(SECOND_WORKFLOW.id, { name: "Renamed Workflow" });
    });
});

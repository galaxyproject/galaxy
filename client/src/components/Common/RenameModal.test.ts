import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { WorkflowSummary } from "@/api/workflows";
import { clickModalButton } from "@/components/BaseComponents/test-utils";
import { updateWorkflow } from "@/components/Workflow/workflows.services";
import { raisedToasts } from "@/composables/__mocks__/toast";

import RenameModal from "./RenameModal.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

vi.mock("@/components/Workflow/workflows.services", () => ({
    updateWorkflow: vi.fn(),
}));

vi.mock("@/composables/toast");

const localVue = getLocalVue();

enableAutoUnmount(afterEach);

const WORKFLOW_ID = "workflow-abc123";
const WORKFLOW_NAME = "My Test Workflow";
const NAME_INPUT = "[data-description='workflow name input']";

async function mountRenameModal() {
    const wrapper = mount(RenameModal, {
        props: {
            name: WORKFLOW_NAME,
            itemType: "workflow",
            renameAction: (newName: string) => updateWorkflow(WORKFLOW_ID, { name: newName }),
        },
        global: localVue,
    });
    await flushPromises();
    return wrapper;
}

async function renameTo(wrapper: VueWrapper, newName: string) {
    await wrapper.find(NAME_INPUT).setValue(newName);
    await clickModalButton(wrapper, "Rename");
}

describe("RenameModal tested for renaming workflows", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("calls updateWorkflow with the new name and emits close on confirm", async () => {
        vi.mocked(updateWorkflow).mockResolvedValue({} as WorkflowSummary);
        const wrapper = await mountRenameModal();

        await renameTo(wrapper, "Renamed Workflow");

        expect(updateWorkflow).toHaveBeenCalledExactlyOnceWith(WORKFLOW_ID, { name: "Renamed Workflow" });
        expect(raisedToasts()).toEqual([{ variant: "success", message: "Workflow renamed" }]);
        expect(wrapper.emitted("close")).toEqual([[]]);
    });

    it("shows an error toast and still emits close when the update fails", async () => {
        vi.mocked(updateWorkflow).mockRejectedValue(new Error("Server error"));
        const wrapper = await mountRenameModal();

        await renameTo(wrapper, "Attempted New Name");

        expect(updateWorkflow).toHaveBeenCalledExactlyOnceWith(WORKFLOW_ID, { name: "Attempted New Name" });
        expect(raisedToasts()).toEqual([{ variant: "error", message: "Server error" }]);
        expect(wrapper.emitted("close")).toEqual([[]]);
    });

    it("starts from the original name when reopened after a failed update", async () => {
        vi.mocked(updateWorkflow).mockRejectedValue(new Error("Server error"));
        const failed = await mountRenameModal();
        await renameTo(failed, "Attempted New Name");
        failed.unmount();

        const reopened = await mountRenameModal();

        expect((reopened.find(NAME_INPUT).element as HTMLInputElement).value).toBe(WORKFLOW_NAME);
    });

    it("keeps ok button disabled when name is unchanged", async () => {
        const wrapper = await mountRenameModal();

        expect(wrapper.findComponent(GModal).props("okDisabled")).toBe(true);
    });
});

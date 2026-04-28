import { getLocalVue } from "@tests/vitest/helpers";
import { createWrapper, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { WorkflowSummary } from "@/api/workflows";
import { updateWorkflow } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";

import RenameModal from "./RenameModal.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

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

async function mountRenameModal(name = WORKFLOW_NAME) {
    const wrapper = mount(RenameModal as object, {
        localVue,
        propsData: {
            name,
            itemType: "workflow",
            renameAction: (newName: string) => updateWorkflow(WORKFLOW_ID, { name: newName }),
        },
        attachTo: document.body,
    });
    await flushPromises();
    return wrapper;
}

describe("RenameModal tested for renaming workflows", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        document.body.innerHTML = "";
    });

    it("calls updateWorkflow with the new name and emits close on confirm", async () => {
        vi.mocked(updateWorkflow).mockResolvedValue({} as WorkflowSummary);

        const wrapper = await mountRenameModal();

        await createWrapper(document.body).find("#workflow-name-input").setValue("Renamed Workflow");
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(updateWorkflow).toHaveBeenCalledWith(WORKFLOW_ID, { name: "Renamed Workflow" });
        expect(wrapper.emitted("close")).toBeTruthy();
    });

    it("shows toast error and emits close when update fails, preserving original name on reopen", async () => {
        vi.mocked(updateWorkflow).mockRejectedValue(new Error("Server error"));

        const wrapper = await mountRenameModal();

        await createWrapper(document.body).find("#workflow-name-input").setValue("Attempted New Name");
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(Toast.error).toHaveBeenCalled();
        expect(updateWorkflow).toHaveBeenCalledWith(WORKFLOW_ID, { name: "Attempted New Name" });
        // close is always emitted (in finally), so the parent can dismiss the modal
        expect(wrapper.emitted("close")).toBeTruthy();

        // Simulate parent closing and reopening the modal (destroys old instance)
        wrapper.unmount();
        await mountRenameModal();
        expect((createWrapper(document.body).find("#workflow-name-input").element as HTMLInputElement).value).toBe(
            WORKFLOW_NAME,
        );
    });

    it("keeps ok button disabled when name is unchanged", async () => {
        const wrapper = await mountRenameModal();

        expect(wrapper.findComponent(GModal).props("okDisabled")).toBe(true);
    });
});

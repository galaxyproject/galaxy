import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref, unref } from "vue";

import type { RegisteredUser } from "@/api";
import type { WorkflowSummary } from "@/api/workflows";
import type { CardAction } from "@/components/Common/GCard.types";
import { useWorkflowCardActions } from "@/components/Workflow/List/useWorkflowCardActions";
import { useUserStore } from "@/stores/userStore";

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm: vi.fn() }),
}));

const OWNER = "owner";

function setup(editorView = false) {
    const workflow = ref({
        id: "workflow_id",
        name: "Workflow",
        owner: OWNER,
        deleted: false,
        published: false,
    } as unknown as WorkflowSummary);
    const noop = () => {};
    return useWorkflowCardActions(workflow, false, editorView, noop, noop, noop);
}

function findAction(actions: CardAction[], id: string) {
    return actions.find((action) => action.id === id);
}

function ids(actions: CardAction[]) {
    return actions.map((action) => action.id);
}

function loadOwner() {
    useUserStore().setCurrentUser({
        id: "user_id",
        email: "owner@example.org",
        username: OWNER,
    } as RegisteredUser);
}

describe("useWorkflowCardActions", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("shows owner actions once the current user loads after setup", () => {
        const { workflowCardExtraActions, workflowCardSecondaryActions, workflowCardPrimaryActions } = setup();

        expect(findAction(unref(workflowCardExtraActions), "workflow-delete")?.visible).toBe(false);
        expect(findAction(unref(workflowCardSecondaryActions), "workflow-share")?.visible).toBe(false);
        expect(findAction(unref(workflowCardPrimaryActions), "workflow-edit")?.visible).toBe(false);
        expect(findAction(unref(workflowCardPrimaryActions), "workflow-import")?.visible).toBe(true);

        loadOwner();

        expect(findAction(unref(workflowCardExtraActions), "workflow-delete")?.visible).toBe(true);
        expect(findAction(unref(workflowCardSecondaryActions), "workflow-share")?.visible).toBe(true);
        expect(findAction(unref(workflowCardPrimaryActions), "workflow-edit")?.visible).toBe(true);
        expect(findAction(unref(workflowCardPrimaryActions), "workflow-import")?.visible).toBe(false);
    });

    it("places common and run actions by view", () => {
        loadOwner();

        const listView = setup(false);
        expect(ids(unref(listView.workflowCardExtraActions))).toEqual([
            "workflow-delete",
            "workflow-export",
            "workflow-view-external-link",
            "workflow-view-external-link",
        ]);
        expect(ids(unref(listView.workflowCardSecondaryActions))).toEqual([
            "workflow-link",
            "workflow-copy",
            "workflow-download",
            "workflow-share",
            "workflow-restore",
            "workflow-copy-steps",
            "workflow-insert-sub-workflow",
        ]);
        expect(ids(unref(listView.workflowCardPrimaryActions))).toEqual([
            "workflow-edit",
            "workflow-import",
            "workflow-run",
        ]);

        const editorView = setup(true);
        expect(ids(unref(editorView.workflowCardExtraActions))).toEqual([
            "workflow-run",
            "workflow-link",
            "workflow-copy",
            "workflow-download",
            "workflow-share",
            "workflow-delete",
            "workflow-export",
            "workflow-view-external-link",
            "workflow-view-external-link",
        ]);
        expect(ids(unref(editorView.workflowCardSecondaryActions))).toEqual([
            "workflow-restore",
            "workflow-copy-steps",
            "workflow-insert-sub-workflow",
        ]);
        expect(ids(unref(editorView.workflowCardPrimaryActions))).toEqual(["workflow-edit", "workflow-import"]);
    });
});

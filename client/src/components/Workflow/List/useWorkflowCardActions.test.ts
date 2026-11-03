import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref, unref } from "vue";

import type { RegisteredUser } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import type { WorkflowSummary } from "@/api/workflows";
import type { CardAction } from "@/components/Common/GCard.types";
import { useWorkflowCardActions } from "@/components/Workflow/List/useWorkflowCardActions";
import { raisedToasts } from "@/composables/__mocks__/toast";
import { useUserStore } from "@/stores/userStore";

const { confirm } = vi.hoisted(() => ({ confirm: vi.fn() }));

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm }),
}));
vi.mock("@/composables/toast");

const { server, http } = useServerMock();

const OWNER = "owner";

function setup(editorView = false, sharedWithMeView = false, refreshCallback = () => {}) {
    const workflow = ref({
        id: "workflow_id",
        name: "Workflow",
        owner: OWNER,
        deleted: false,
        published: false,
    } as unknown as WorkflowSummary);
    const noop = () => {};
    return useWorkflowCardActions(workflow, false, editorView, refreshCallback, noop, noop, sharedWithMeView);
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
        vi.clearAllMocks();
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
            "workflow-unshare-with-me",
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
            "workflow-unshare-with-me",
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

    it("offers removing a shared workflow only in the shared with me view", () => {
        expect(
            findAction(unref(setup(false, true).workflowCardExtraActions), "workflow-unshare-with-me")?.visible,
        ).toBe(true);
        expect(findAction(unref(setup().workflowCardExtraActions), "workflow-unshare-with-me")?.visible).toBe(false);
    });

    it("keeps the share when removal is not confirmed", async () => {
        const unshared: string[] = [];
        server.use(
            http.put("/api/workflows/{workflow_id}/unshare_with_me", ({ params, response }) => {
                unshared.push(params.workflow_id);
                return response(204).empty();
            }),
        );
        confirm.mockResolvedValue(false);
        const refresh = vi.fn();

        const action = findAction(
            unref(setup(false, true, refresh).workflowCardExtraActions),
            "workflow-unshare-with-me",
        );
        expect(action?.handler).toBeDefined();
        await action?.handler?.();
        await flushPromises();

        expect(confirm).toHaveBeenCalledTimes(1);
        expect(unshared).toEqual([]);
        expect(refresh).not.toHaveBeenCalled();
        expect(raisedToasts()).toEqual([]);
    });

    it("reports a failed removal without refreshing", async () => {
        server.use(
            http.put("/api/workflows/{workflow_id}/unshare_with_me", ({ response }) => {
                return response("4XX").json({ err_msg: "Workflow not found", err_code: 404 }, { status: 404 });
            }),
        );
        confirm.mockResolvedValue(true);
        const refresh = vi.fn();

        const action = findAction(
            unref(setup(false, true, refresh).workflowCardExtraActions),
            "workflow-unshare-with-me",
        );
        await action?.handler?.();
        await flushPromises();

        expect(refresh).not.toHaveBeenCalled();
        expect(raisedToasts()).toEqual([
            { variant: "error", message: "Failed to remove shared workflow: Workflow not found" },
        ]);
    });
});

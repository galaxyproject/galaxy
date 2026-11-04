import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref, unref } from "vue";

import type { RegisteredUser } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import type { AnyHistoryEntry } from "@/api/histories";
import type { CardAction } from "@/components/Common/GCard.types";
import { useHistoryCardActions } from "@/components/History/useHistoryCardActions";
import { raisedToasts } from "@/composables/__mocks__/toast";
import { useUserStore } from "@/stores/userStore";

const { confirm } = vi.hoisted(() => ({ confirm: vi.fn() }));

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm }),
}));
vi.mock("@/composables/toast");

const { server, http } = useServerMock();

const OWNER = "owner";

function findAction(actions: CardAction[], id: string) {
    return actions.find((action) => action.id === id);
}

function sharedHistory() {
    return ref({
        id: "history_id",
        name: "Shared History",
        username: OWNER,
        deleted: false,
        purged: false,
    } as unknown as AnyHistoryEntry);
}

describe("useHistoryCardActions", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.clearAllMocks();
    });

    it("shows owner actions once the current user loads after setup", () => {
        const history = ref({
            id: "history_id",
            name: "History",
            username: OWNER,
            deleted: false,
            purged: false,
        } as unknown as AnyHistoryEntry);

        const { historyCardExtraActions, historyCardSecondaryActions } = useHistoryCardActions(
            history,
            false,
            () => {},
        );

        expect(findAction(unref(historyCardSecondaryActions), "share-access-management")?.visible).toBe(false);
        expect(findAction(unref(historyCardExtraActions), "delete")?.visible).toBe(false);
        expect(findAction(unref(historyCardExtraActions), "purge")?.visible).toBe(false);

        useUserStore().setCurrentUser({
            id: "user_id",
            email: "owner@example.org",
            username: OWNER,
        } as RegisteredUser);

        expect(findAction(unref(historyCardSecondaryActions), "share-access-management")?.visible).toBe(true);
        expect(findAction(unref(historyCardExtraActions), "delete")?.visible).toBe(true);
        expect(findAction(unref(historyCardExtraActions), "purge")?.visible).toBe(true);
    });

    it("offers removing a shared history only in the shared view", () => {
        const sharedActions = useHistoryCardActions(sharedHistory(), false, () => {}, true);
        expect(findAction(unref(sharedActions.historyCardExtraActions), "unshare-with-me")?.visible).toBe(true);

        const otherActions = useHistoryCardActions(sharedHistory(), false, () => {});
        expect(findAction(unref(otherActions.historyCardExtraActions), "unshare-with-me")?.visible).toBe(false);
    });

    it("keeps the share when removal is not confirmed", async () => {
        const unshared: string[] = [];
        server.use(
            http.put("/api/histories/{history_id}/unshare_with_me", ({ params, response }) => {
                unshared.push(params.history_id);
                return response(204).empty();
            }),
        );
        confirm.mockResolvedValue(false);
        const refresh = vi.fn();

        const { historyCardExtraActions } = useHistoryCardActions(sharedHistory(), false, refresh, true);
        const action = findAction(unref(historyCardExtraActions), "unshare-with-me");
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
            http.put("/api/histories/{history_id}/unshare_with_me", ({ response }) => {
                return response("4XX").json({ err_msg: "History not found", err_code: 404 }, { status: 404 });
            }),
        );
        confirm.mockResolvedValue(true);
        const refresh = vi.fn();

        const { historyCardExtraActions } = useHistoryCardActions(sharedHistory(), false, refresh, true);
        await findAction(unref(historyCardExtraActions), "unshare-with-me")?.handler?.();
        await flushPromises();

        expect(refresh).not.toHaveBeenCalled();
        expect(raisedToasts()).toEqual([
            { variant: "error", message: "Failed to remove shared history: History not found" },
        ]);
    });
});

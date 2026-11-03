import { getFakeHistorySummary, getFakeRegisteredUser } from "@tests/test-data";
import { runInTestScope } from "@tests/vitest/effectScope";
import flushPromises from "flush-promises";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { ref, unref } from "vue";

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

function getAction(actions: CardAction[], id: string): CardAction {
    const action = actions.find((action) => action.id === id);
    if (!action) {
        throw new Error(`Missing history card action: ${id}`);
    }
    return action;
}

/** Activates a pinia disposed when the current test finishes. */
function setupPinia() {
    const pinia = createPinia();
    setActivePinia(pinia);
    onTestFinished(() => disposePinia(pinia));
    return pinia;
}

function ownersHistory(name: string) {
    return ref<AnyHistoryEntry>({ ...getFakeHistorySummary({ id: "history_id", name }), username: OWNER });
}

/** Card actions for the owner's history, listed in the shared-with-me view when `sharedWithMeView`. */
function setupSharedHistoryActions(refresh: () => void, sharedWithMeView = true) {
    setupPinia();
    return runInTestScope(() =>
        useHistoryCardActions(ownersHistory("Shared History"), false, refresh, sharedWithMeView),
    );
}

describe("useHistoryCardActions", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("shows owner actions once the current user loads after setup", () => {
        const userStore = useUserStore(setupPinia());
        const history = ownersHistory("History");

        const { historyCardExtraActions, historyCardSecondaryActions } = runInTestScope(() =>
            useHistoryCardActions(history, false, vi.fn()),
        );

        expect(getAction(unref(historyCardSecondaryActions), "share-access-management").visible).toBe(false);
        expect(getAction(unref(historyCardExtraActions), "delete").visible).toBe(false);
        expect(getAction(unref(historyCardExtraActions), "purge").visible).toBe(false);

        userStore.setCurrentUser(getFakeRegisteredUser({ id: "user_id", email: "owner@example.org", username: OWNER }));

        expect(getAction(unref(historyCardSecondaryActions), "share-access-management").visible).toBe(true);
        expect(getAction(unref(historyCardExtraActions), "delete").visible).toBe(true);
        expect(getAction(unref(historyCardExtraActions), "purge").visible).toBe(true);
    });

    it("offers removing a shared history only in the shared view", () => {
        const sharedActions = setupSharedHistoryActions(() => {});
        expect(getAction(unref(sharedActions.historyCardExtraActions), "unshare-with-me").visible).toBe(true);

        const otherActions = setupSharedHistoryActions(() => {}, false);
        expect(getAction(unref(otherActions.historyCardExtraActions), "unshare-with-me").visible).toBe(false);
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

        const { historyCardExtraActions } = setupSharedHistoryActions(refresh);
        const action = getAction(unref(historyCardExtraActions), "unshare-with-me");
        expect(action.handler).toBeDefined();
        await action.handler?.();
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

        const { historyCardExtraActions } = setupSharedHistoryActions(refresh);
        await getAction(unref(historyCardExtraActions), "unshare-with-me").handler?.();
        await flushPromises();

        expect(refresh).not.toHaveBeenCalled();
        expect(raisedToasts()).toEqual([
            { variant: "error", message: "Failed to remove shared history: History not found" },
        ]);
    });
});

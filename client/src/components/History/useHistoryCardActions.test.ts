import { getFakeHistorySummary, getFakeRegisteredUser } from "@tests/test-data";
import { runInTestScope } from "@tests/vitest/effectScope";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import { describe, expect, it, onTestFinished, vi } from "vitest";
import { ref, unref } from "vue";

import type { AnyHistoryEntry } from "@/api/histories";
import type { CardAction } from "@/components/Common/GCard.types";
import { useHistoryCardActions } from "@/components/History/useHistoryCardActions";
import { useUserStore } from "@/stores/userStore";

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm: vi.fn() }),
}));

const OWNER = "owner";

function getAction(actions: CardAction[], id: string): CardAction {
    const action = actions.find((action) => action.id === id);
    if (!action) {
        throw new Error(`Missing history card action: ${id}`);
    }
    return action;
}

describe("useHistoryCardActions", () => {
    it("shows owner actions once the current user loads after setup", () => {
        const pinia = createPinia();
        setActivePinia(pinia);
        onTestFinished(() => disposePinia(pinia));
        const userStore = useUserStore(pinia);
        const history = ref<AnyHistoryEntry>({
            ...getFakeHistorySummary({ id: "history_id", name: "History" }),
            username: OWNER,
        });

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
});

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref, unref } from "vue";

import type { RegisteredUser } from "@/api";
import type { AnyHistoryEntry } from "@/api/histories";
import type { CardAction } from "@/components/Common/GCard.types";
import { useHistoryCardActions } from "@/components/History/useHistoryCardActions";
import { useUserStore } from "@/stores/userStore";

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm: vi.fn() }),
}));

const OWNER = "owner";

function findAction(actions: CardAction[], id: string) {
    return actions.find((action) => action.id === id);
}

describe("useHistoryCardActions", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
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
});

import { getFakeRegisteredUser } from "@tests/test-data";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { AnyHistoryEntry } from "@/api/histories";
import { useUserStore } from "@/stores/userStore";

import { useHistoryCardBadges } from "./useHistoryCardBadges";

const OWNER = "jdoe";

function ownerBadge(history: object, sharedView: boolean, publishedView: boolean, id: string) {
    const updateFilter = vi.fn();
    const { historyCardTitleBadges } = useHistoryCardBadges(
        ref(history as AnyHistoryEntry),
        sharedView,
        publishedView,
        updateFilter,
    );
    return { badge: historyCardTitleBadges.find((b) => b.id === id), updateFilter };
}

describe("useHistoryCardBadges", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        useUserStore().currentUser = getFakeRegisteredUser({ username: "someone_else" });
    });

    it.each([
        ["owner-shared", { id: "h1", username: OWNER }, true, false],
        ["owner-published", { id: "h1", username: OWNER, published: true }, false, true],
    ])("names the %s badge after the filter it applies", (id, history, sharedView, publishedView) => {
        const { badge, updateFilter } = ownerBadge(history, sharedView, publishedView, id);

        expect(badge?.visible).toBe(true);
        expect(badge?.ariaLabel).toBe(`Filter by owner ${OWNER}`);
        badge?.handler?.();
        expect(updateFilter).toHaveBeenCalledWith("user", OWNER);
    });
});

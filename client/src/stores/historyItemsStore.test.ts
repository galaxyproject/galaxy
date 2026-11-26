import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { urlData } from "@/utils/url";

vi.mock("@/utils/url", () => ({ urlData: vi.fn() }));

const totalsByHistory: Record<string, number> = { "history-a": 19, "history-b": 12 };

describe("useHistoryItemsStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.mocked(urlData).mockImplementation(async ({ url }: { url: string }) => {
            const historyId = Object.keys(totalsByHistory).find((id) => url.includes(`/histories/${id}/`));
            return { stats: { total_matches: totalsByHistory[historyId as string] }, contents: [] };
        });
    });

    it("keeps the total match count of each history separate", async () => {
        const store = useHistoryItemsStore();

        await store.fetchHistoryItems("history-a", "", 0);
        await store.fetchHistoryItems("history-b", "", 0);

        expect(store.getTotalMatchesCount("history-a")).toBe(19);
        expect(store.getTotalMatchesCount("history-b")).toBe(12);
    });

    it("has no total match count for a history that was never loaded", () => {
        const store = useHistoryItemsStore();

        expect(store.getTotalMatchesCount("history-a")).toBeUndefined();
    });
});

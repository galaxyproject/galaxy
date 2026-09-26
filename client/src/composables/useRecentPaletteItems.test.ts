import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";

import type { RecentPaletteItem } from "./useRecentPaletteItems";

const hashedUserId = ref<string | null>("test-hash");

vi.mock("@/stores/userStore", () => ({
    useUserStore: () => ({ currentUser: null }),
}));

vi.mock("@/composables/hashedUserId", () => ({
    useHashedUserId: () => ({ hashedUserId }),
}));

const STORAGE_KEY = "command-palette-recent-items-test-hash";

async function loadComposable() {
    vi.resetModules();
    const { useRecentPaletteItems, RECENT_PALETTE_ITEMS_LIMIT } = await import("./useRecentPaletteItems");
    return { ...useRecentPaletteItems(), RECENT_PALETTE_ITEMS_LIMIT };
}

function item(type: string, id: string, name = `${type} ${id}`): RecentPaletteItem {
    return { type, id, name, to: `/${type}/${id}` };
}

describe("useRecentPaletteItems", () => {
    beforeEach(() => {
        hashedUserId.value = "test-hash";
        window.localStorage.clear();
    });

    it("returns no items for an unknown type", async () => {
        const { recentItems } = await loadComposable();

        expect(recentItems("history")).toEqual([]);
        expect(recentItems("")).toEqual([]);
    });

    it("keeps items per type in most recently used order", async () => {
        const { addRecentItem, recentItems } = await loadComposable();

        addRecentItem(item("history", "1"));
        addRecentItem(item("workflow", "1"));
        addRecentItem(item("history", "2"));

        expect(recentItems("history").map((entry) => entry.id)).toEqual(["2", "1"]);
        expect(recentItems("workflow").map((entry) => entry.id)).toEqual(["1"]);
    });

    it("deduplicates by type and id, moving the item to the front", async () => {
        const { addRecentItem, recentItems } = await loadComposable();

        addRecentItem(item("history", "1", "first name"));
        addRecentItem(item("history", "2"));
        addRecentItem(item("history", "1", "renamed"));

        expect(recentItems("history")).toEqual([
            { type: "history", id: "1", name: "renamed", to: "/history/1" },
            { type: "history", id: "2", name: "history 2", to: "/history/2" },
        ]);
    });

    it("treats identical ids of different types as distinct items", async () => {
        const { addRecentItem, recentItems } = await loadComposable();

        addRecentItem(item("history", "shared-id"));
        addRecentItem(item("dataset", "shared-id"));

        expect(recentItems("history")).toHaveLength(1);
        expect(recentItems("dataset")).toHaveLength(1);
    });

    it("caps the remembered items per type", async () => {
        const { addRecentItem, recentItems, RECENT_PALETTE_ITEMS_LIMIT } = await loadComposable();

        for (let index = 0; index < RECENT_PALETTE_ITEMS_LIMIT + 5; index++) {
            addRecentItem(item("dataset", `${index}`));
        }

        const ids = recentItems("dataset").map((entry) => entry.id);
        expect(ids).toHaveLength(RECENT_PALETTE_ITEMS_LIMIT);
        expect(ids[0]).toBe(`${RECENT_PALETTE_ITEMS_LIMIT + 4}`);
        expect(ids[ids.length - 1]).toBe("5");
    });

    it("ignores entries without a type or an id", async () => {
        const { addRecentItem, recentItems } = await loadComposable();

        addRecentItem({ type: "", id: "1", name: "no type" });
        addRecentItem({ type: "history", id: "", name: "no id" });

        expect(recentItems("history")).toEqual([]);
        expect(recentItems("")).toEqual([]);
    });

    it("stores items without a route", async () => {
        const { addRecentItem, recentItems } = await loadComposable();

        addRecentItem({ type: "tool", id: "cat1", name: "Concatenate" });

        expect(recentItems("tool")).toEqual([{ type: "tool", id: "cat1", name: "Concatenate" }]);
    });

    it("clears a single type, or every type", async () => {
        const { addRecentItem, clearRecentItems, recentItems } = await loadComposable();

        addRecentItem(item("history", "1"));
        addRecentItem(item("workflow", "1"));

        clearRecentItems("history");
        expect(recentItems("history")).toEqual([]);
        expect(recentItems("workflow")).toHaveLength(1);

        clearRecentItems();
        expect(recentItems("workflow")).toEqual([]);
    });

    it("persists items to local storage for the hashed user", async () => {
        const { addRecentItem } = await loadComposable();

        addRecentItem(item("page", "abc"));
        await nextTick();

        expect(JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "{}")).toEqual({
            page: [{ type: "page", id: "abc", name: "page abc", to: "/page/abc" }],
        });
    });

    it("restores items persisted for the hashed user", async () => {
        window.localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ page: [{ type: "page", id: "abc", name: "Persisted page" }] }),
        );

        const { recentItems } = await loadComposable();

        expect(recentItems("page")).toEqual([{ type: "page", id: "abc", name: "Persisted page" }]);
    });

    it("discards malformed persisted entries", async () => {
        window.localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ page: [{ id: "abc" }, null, "nope"], history: "not-an-array" }),
        );

        const { recentItems } = await loadComposable();

        expect(recentItems("page")).toEqual([]);
        expect(recentItems("history")).toEqual([]);
    });

    it("shares state between consumers", async () => {
        const { addRecentItem } = await loadComposable();
        const { useRecentPaletteItems } = await import("./useRecentPaletteItems");

        addRecentItem(item("history", "1"));

        expect(useRecentPaletteItems().recentItems("history")).toHaveLength(1);
    });
});

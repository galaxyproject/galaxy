import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PaletteItem } from "../types";
import { PaletteFetchError } from "./errors";
import { resetListRefreshTracking } from "./refresh";
import { rootListItems, storeFirstItems } from "./storeFirst";

function row(id: string, title: string): PaletteItem {
    return { id: `fake:${id}`, mru: { type: "fake", id }, title };
}

const ALPHA = row("1", "alpha");
const ALPINE = row("2", "alpine");
const REMOTE = row("3", "alpaca");

/** A list whose listing holds ALPHA and ALPINE and whose backend search finds REMOTE */
function fakeList() {
    const state = { complete: false, loaded: false };
    return {
        state,
        key: "fake:my",
        isLoaded: () => state.loaded,
        fetchListing: vi.fn<() => Promise<void>>(async () => {
            state.loaded = true;
        }),
        cachedItems: (): PaletteItem[] => (state.loaded ? [ALPHA, ALPINE] : []),
        isComplete: () => state.complete,
        searchItems: vi.fn<(query: string) => Promise<PaletteItem[]>>(async () => [REMOTE, ALPHA]),
    };
}

describe("storeFirstItems", () => {
    beforeEach(() => {
        resetListRefreshTracking();
    });

    it("hydrates the listing once and answers later keystrokes from the cache", async () => {
        const list = fakeList();

        await storeFirstItems(list, "", 8);
        const items = await storeFirstItems(list, "alp", 1);

        expect(items.map((item) => item.title)).toEqual(["alpha"]);
        expect(list.fetchListing).toHaveBeenCalledTimes(1);
        expect(list.searchItems).not.toHaveBeenCalled();
    });

    it("reports a listing whose very first fetch failed", async () => {
        const list = fakeList();
        list.fetchListing.mockRejectedValue(new Error("boom"));

        await expect(storeFirstItems(list, "", 8)).rejects.toBeInstanceOf(PaletteFetchError);
    });

    it("only asks the backend for a long enough query an incomplete cache cannot fill", async () => {
        const list = fakeList();

        await storeFirstItems(list, "a", 8);
        await storeFirstItems(list, "alp", 8, { cacheOnly: true });
        list.state.complete = true;
        await storeFirstItems(list, "alp", 8);
        expect(list.searchItems).not.toHaveBeenCalled();

        list.state.complete = false;
        await storeFirstItems(list, "alp", 8);
        expect(list.searchItems).toHaveBeenCalledWith("alp");
    });

    it("merges the found rows into the cached ones, one row per entity", async () => {
        const items = await storeFirstItems(fakeList(), "alp", 8);

        expect(items.map((item) => item.title).sort()).toEqual(["alpaca", "alpha", "alpine"]);
    });

    it("keeps the cached rows when the search fails", async () => {
        const list = fakeList();
        list.searchItems.mockRejectedValue(new Error("boom"));

        const items = await storeFirstItems(list, "alp", 8);

        expect(items.map((item) => item.title).sort()).toEqual(["alpha", "alpine"]);
    });
});

describe("rootListItems", () => {
    it("answers from the cached own rows and the searched listings, one row per entity", async () => {
        const own = fakeList();
        await own.fetchListing();
        const failing = vi.fn(async () => {
            throw new Error("boom");
        });

        const items = await rootListItems("alp", own, [async () => [REMOTE, ALPHA], failing]);

        expect(items.map((item) => item.title).sort()).toEqual(["alpaca", "alpha", "alpine"]);
        expect(own.fetchListing).toHaveBeenCalledTimes(1);
        expect(failing).toHaveBeenCalledWith("alp");
    });

    it("skips the listing searches for a short or local-only query", async () => {
        const listing = vi.fn(async () => [REMOTE]);

        expect(await rootListItems("a", undefined, [listing])).toEqual([]);
        expect(await rootListItems("alp", undefined, [listing], { localOnly: true })).toEqual([]);
        expect(listing).not.toHaveBeenCalled();
    });
});

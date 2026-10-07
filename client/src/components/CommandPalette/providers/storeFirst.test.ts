import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { PaletteItem } from "../types";
import { PaletteFetchError } from "./errors";
import { PALETTE_LIMITS } from "./limits";
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
    beforeEach(() => {
        resetListRefreshTracking();
    });

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

    it("hydrates an unloaded own list once, so a first search finds own rows", async () => {
        const own = fakeList();

        const first = await rootListItems("alp", own, []);
        await rootListItems("alpi", own, []);

        expect(first.map((item) => item.title).sort()).toEqual(["alpha", "alpine"]);
        expect(own.fetchListing).toHaveBeenCalledTimes(1);
        expect(own.searchItems).not.toHaveBeenCalled();
    });

    it("answers with the listings alone when the own list fails to hydrate", async () => {
        const own = fakeList();
        own.fetchListing.mockRejectedValue(new Error("boom"));

        const items = await rootListItems("alp", own, [async () => [REMOTE]]);

        expect(items.map((item) => item.title)).toEqual(["alpaca"]);
    });

    it("caps the answer at the rows a fan-out section shows", async () => {
        const many = Array.from({ length: 10 }, (_, index) => row(`m${index}`, `alpine ${index}`));

        const items = await rootListItems(
            "alp",
            undefined,
            [0, 3, 6].map((start) => async () => many.slice(start, start + 3)),
        );

        expect(items).toHaveLength(PALETTE_LIMITS.section);
    });

    it("skips the listing searches and the hydration for a short or local-only query", async () => {
        const listing = vi.fn(async () => [REMOTE]);
        const own = fakeList();

        expect(await rootListItems("a", own, [listing])).toEqual([]);
        expect(await rootListItems("alp", own, [listing], { localOnly: true })).toEqual([]);
        expect(listing).not.toHaveBeenCalled();
        expect(own.fetchListing).not.toHaveBeenCalled();
    });

    describe("with a signal a newer search can abort", () => {
        beforeEach(() => {
            vi.useFakeTimers();
        });

        afterEach(() => {
            vi.useRealTimers();
        });

        it("waits for the input to settle before searching the listings", async () => {
            const listing = vi.fn(async () => [REMOTE]);
            const controller = new AbortController();

            const answer = rootListItems("alp", undefined, [listing], { signal: controller.signal });
            await vi.advanceTimersByTimeAsync(PALETTE_LIMITS.backendSettle - 1);
            expect(listing).not.toHaveBeenCalled();
            await vi.advanceTimersByTimeAsync(1);

            expect((await answer).map((item) => item.title)).toEqual(["alpaca"]);
            expect(listing).toHaveBeenCalledWith("alp");
        });

        it("never searches the listings once a newer search took over", async () => {
            const listing = vi.fn(async () => [REMOTE]);
            const own = fakeList();
            await own.fetchListing();
            const controller = new AbortController();

            const answer = rootListItems("alp", own, [listing], { signal: controller.signal });
            controller.abort();
            await vi.advanceTimersByTimeAsync(PALETTE_LIMITS.backendSettle);

            expect((await answer).map((item) => item.title).sort()).toEqual(["alpha", "alpine"]);
            expect(listing).not.toHaveBeenCalled();
        });
    });
});

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AnyHistoryEntry } from "@/api/histories";

import { sseMockFactory } from "./_testing/sseStoreSupport";
import { useHistoryStore } from "./historyStore";

const sseState = vi.hoisted(() => {
    return {
        onEvent: null as ((event: MessageEvent) => void) | null,
        connect: vi.fn(),
        disconnect: vi.fn(),
    };
});

vi.mock("@/composables/useNotificationSSE", () => sseMockFactory(sseState));

vi.mock("@/watch/watchHistory", () => ({
    ACTIVE_POLLING_INTERVAL: 3000,
    INACTIVE_POLLING_INTERVAL: 60_000,
    watchHistory: vi.fn().mockResolvedValue(undefined),
    refreshHistoryFromPush: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/app", () => ({
    getGalaxyInstance: () => ({ name: "fake-galaxy" }),
}));

const { getSharedHistories, getPublishedHistories, getArchivedHistories } = vi.hoisted(() => ({
    getSharedHistories: vi.fn(),
    getPublishedHistories: vi.fn(),
    getArchivedHistories: vi.fn(),
}));

vi.mock("@/api/histories", () => ({
    getSharedHistories,
    getPublishedHistories,
    getArchivedHistories,
}));

function mockHistory(id: string, name: string, updateTime: string, extra: Record<string, unknown> = {}) {
    return {
        id,
        name,
        model_class: "History",
        update_time: updateTime,
        username: "other-user",
        ...extra,
    } as unknown as AnyHistoryEntry;
}

function resultOf(histories: AnyHistoryEntry[], total = histories.length) {
    return { data: histories, total };
}

describe("historyStore — cached history listings", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.clearAllMocks();
        getSharedHistories.mockResolvedValue(resultOf([]));
        getPublishedHistories.mockResolvedValue(resultOf([]));
        getArchivedHistories.mockResolvedValue(resultOf([]));
    });

    it("fetches shared histories with update_time descending defaults", async () => {
        const store = useHistoryStore();
        getSharedHistories.mockResolvedValue(resultOf([mockHistory("h1", "Shared", "2026-01-01T00:00:00")], 12));

        const fetched = await store.fetchHistoryList("shared");

        expect(getSharedHistories).toHaveBeenCalledWith({
            limit: 25,
            offset: 0,
            search: "",
            sortBy: "update_time",
            sortDesc: true,
        });
        expect(fetched.map((history) => history.id)).toEqual(["h1"]);
        expect(store.sharedHistories.map((history) => history.id)).toEqual(["h1"]);
        expect(store.getHistoryListTotal("shared")).toBe(12);
        expect(store.hasLoadedHistoryList("shared")).toBe(true);
    });

    it("forwards an optional search query and pagination options", async () => {
        const store = useHistoryStore();

        await store.fetchHistoryList("published", { search: "rna", limit: 5, offset: 10, sortBy: "name" });

        expect(getPublishedHistories).toHaveBeenCalledWith({
            limit: 5,
            offset: 10,
            search: "rna",
            sortBy: "name",
            sortDesc: true,
        });
    });

    it("fetches archived histories through the archived endpoint wrapper", async () => {
        const store = useHistoryStore();
        getArchivedHistories.mockResolvedValue(
            resultOf([mockHistory("a1", "Archived", "2026-01-01T00:00:00", { archived: true })]),
        );

        await store.fetchHistoryList("archived");

        expect(getArchivedHistories).toHaveBeenCalledTimes(1);
        expect(store.archivedHistories.map((history) => history.id)).toEqual(["a1"]);
    });

    it("sorts cached entries by update time, most recent first", async () => {
        const store = useHistoryStore();
        getPublishedHistories.mockResolvedValue(
            resultOf([
                mockHistory("old", "Old", "2026-01-01T00:00:00"),
                mockHistory("new", "New", "2026-03-01T00:00:00"),
                mockHistory("mid", "Mid", "2026-02-01T00:00:00"),
            ]),
        );

        await store.fetchHistoryList("published");

        expect(store.publishedHistories.map((history) => history.id)).toEqual(["new", "mid", "old"]);
    });

    it("merges repeated fetches without duplicating ids", async () => {
        const store = useHistoryStore();
        getSharedHistories.mockResolvedValueOnce(
            resultOf([
                mockHistory("h1", "One", "2026-01-01T00:00:00"),
                mockHistory("h2", "Two", "2026-01-02T00:00:00"),
            ]),
        );
        getSharedHistories.mockResolvedValueOnce(
            resultOf([
                mockHistory("h2", "Two", "2026-01-02T00:00:00"),
                mockHistory("h3", "Three", "2026-01-03T00:00:00"),
            ]),
        );

        await store.fetchHistoryList("shared");
        await store.fetchHistoryList("shared", { search: "t" });

        expect(store.listedHistoryIds.shared).toEqual(["h1", "h2", "h3"]);
        expect(store.sharedHistories).toHaveLength(3);
    });

    it("keeps already cached fields when a later fetch returns a leaner summary", async () => {
        const store = useHistoryStore();
        getSharedHistories.mockResolvedValueOnce(
            resultOf([mockHistory("h1", "One", "2026-01-01T00:00:00", { owner: "someone" })]),
        );
        getSharedHistories.mockResolvedValueOnce(resultOf([mockHistory("h1", "One renamed", "2026-01-05T00:00:00")]));

        await store.fetchHistoryList("shared");
        await store.fetchHistoryList("shared");

        const cached = store.listedHistories["h1"] as AnyHistoryEntry & { owner?: string };
        expect(cached.owner).toBe("someone");
        expect(cached.name).toBe("One renamed");
    });

    it("replaces the cached ids of a listing when asked to", async () => {
        const store = useHistoryStore();
        getSharedHistories.mockResolvedValueOnce(resultOf([mockHistory("h1", "One", "2026-01-01T00:00:00")]));
        getSharedHistories.mockResolvedValueOnce(resultOf([mockHistory("h2", "Two", "2026-01-02T00:00:00")]));

        await store.fetchHistoryList("shared");
        await store.fetchHistoryList("shared", { replace: true });

        expect(store.listedHistoryIds.shared).toEqual(["h2"]);
    });

    it("keeps the listings separate while sharing a single summary map", async () => {
        const store = useHistoryStore();
        getSharedHistories.mockResolvedValue(resultOf([mockHistory("h1", "Shared", "2026-01-01T00:00:00")]));
        getPublishedHistories.mockResolvedValue(resultOf([mockHistory("h1", "Shared", "2026-01-01T00:00:00")]));

        await store.fetchHistoryList("shared");
        await store.fetchHistoryList("published");

        expect(store.listedHistoryIds.shared).toEqual(["h1"]);
        expect(store.listedHistoryIds.published).toEqual(["h1"]);
        expect(store.listedHistoryIds.archived).toEqual([]);
        expect(Object.keys(store.listedHistories)).toEqual(["h1"]);
    });

    it("never adds listed histories to the current user's own histories", async () => {
        const store = useHistoryStore();
        getPublishedHistories.mockResolvedValue(resultOf([mockHistory("foreign", "Someone else", "2026-01-01")]));

        await store.fetchHistoryList("published");

        expect(store.histories).toEqual([]);
        expect(store.storedHistories).toEqual({});
    });

    it("clears the loading flag and rethrows when a fetch fails", async () => {
        const store = useHistoryStore();
        getSharedHistories.mockRejectedValue(new Error("boom"));

        await expect(store.fetchHistoryList("shared")).rejects.toThrow();
        expect(store.isHistoryListLoading("shared")).toBe(false);
        expect(store.hasLoadedHistoryList("shared")).toBe(false);
    });

    it("only fetches a listing once via ensureHistoryListLoaded", async () => {
        const store = useHistoryStore();
        getSharedHistories.mockResolvedValue(resultOf([mockHistory("h1", "One", "2026-01-01T00:00:00")]));

        await store.ensureHistoryListLoaded("shared");
        const cached = await store.ensureHistoryListLoaded("shared");

        expect(getSharedHistories).toHaveBeenCalledTimes(1);
        expect(cached.map((history) => history.id)).toEqual(["h1"]);
    });

    it("shares a running fetch instead of returning the still empty listing", async () => {
        const store = useHistoryStore();
        let resolveFetch: (result: { data: AnyHistoryEntry[]; total: number }) => void = () => undefined;
        getSharedHistories.mockReturnValue(
            new Promise((resolve) => {
                resolveFetch = resolve;
            }),
        );

        const hydrating = store.ensureHistoryListLoaded("shared");
        const duringFetch = store.ensureHistoryListLoaded("shared");
        resolveFetch(resultOf([mockHistory("h1", "One", "2026-01-01T00:00:00")]));
        const [first, second] = await Promise.all([hydrating, duringFetch]);

        expect(getSharedHistories).toHaveBeenCalledTimes(1);
        expect(first.map((history) => history.id)).toEqual(["h1"]);
        expect(second.map((history) => history.id)).toEqual(["h1"]);
    });

    it("deduplicates identical concurrent fetches of a listing", async () => {
        const store = useHistoryStore();
        getSharedHistories.mockResolvedValue(resultOf([mockHistory("h1", "One", "2026-01-01T00:00:00")]));

        const [first, second] = await Promise.all([store.fetchHistoryList("shared"), store.fetchHistoryList("shared")]);

        expect(getSharedHistories).toHaveBeenCalledTimes(1);
        expect(first).toEqual(second);
    });

    it("hydrates the canonical listing independently of a one-off search", async () => {
        const store = useHistoryStore();
        let resolveSearch: (result: { data: AnyHistoryEntry[]; total: number }) => void = () => undefined;
        let resolveCanonical: (result: { data: AnyHistoryEntry[]; total: number }) => void = () => undefined;
        getSharedHistories.mockImplementation(({ search }: { search: string }) => {
            return new Promise((resolve) => {
                if (search) {
                    resolveSearch = resolve;
                } else {
                    resolveCanonical = resolve;
                }
            });
        });

        const search = store.fetchHistoryList("shared", { search: "needle", record: false });
        const hydration = store.ensureHistoryListLoaded("shared");

        expect(getSharedHistories).toHaveBeenCalledTimes(2);
        resolveSearch(resultOf([mockHistory("search-hit", "Needle", "2026-01-01T00:00:00")], 1));
        resolveCanonical(resultOf([mockHistory("canonical-hit", "Latest", "2026-02-01T00:00:00")], 5));
        const [, canonical] = await Promise.all([search, hydration]);

        expect(canonical.map((history) => history.id)).toEqual(["canonical-hit"]);
        expect(store.listedHistoryIds.shared).toEqual(["canonical-hit"]);
        expect(store.listedHistories["search-hit"]).toBeDefined();
        expect(store.getHistoryListTotal("shared")).toBe(5);
        expect(store.hasLoadedHistoryList("shared")).toBe(true);
    });

    it("re-fetches after the cached listing has been cleared", async () => {
        const store = useHistoryStore();
        getSharedHistories.mockResolvedValue(resultOf([mockHistory("h1", "One", "2026-01-01T00:00:00")]));

        await store.ensureHistoryListLoaded("shared");
        store.clearHistoryList("shared");

        expect(store.sharedHistories).toEqual([]);
        expect(store.getHistoryListTotal("shared")).toBe(0);

        await store.ensureHistoryListLoaded("shared");
        expect(getSharedHistories).toHaveBeenCalledTimes(2);
    });
});

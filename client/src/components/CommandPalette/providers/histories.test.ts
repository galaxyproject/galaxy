import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RecentPaletteItem } from "@/composables/useRecentPaletteItems";
import { sseMockFactory } from "@/stores/_testing/sseStoreSupport";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import type { PaletteContext } from "../types";
import { historiesProvider } from "./histories";
import type { ScopeDefinition } from "./scopes";

const sseState = vi.hoisted(() => ({
    onEvent: null as ((event: MessageEvent) => void) | null,
    connect: vi.fn(),
    disconnect: vi.fn(),
}));

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

const { getHistoryList, setCurrentHistoryOnServer } = vi.hoisted(() => ({
    getHistoryList: vi.fn(),
    setCurrentHistoryOnServer: vi.fn(),
}));

vi.mock("@/stores/services/history.services", () => ({
    createAndSelectNewHistory: vi.fn(),
    getCurrentHistoryFromServer: vi.fn(),
    getHistoryByIdFromServer: vi.fn(),
    getHistoryList,
    secureHistoryOnServer: vi.fn(),
    setCurrentHistoryOnServer,
    updateHistoryFields: vi.fn(),
}));

let recent: RecentPaletteItem[] = [];

vi.mock("@/composables/useRecentPaletteItems", () => ({
    useRecentPaletteItems: () => ({
        recentItems: (type: string) => (type === "history" ? recent : []),
        addRecentItem: vi.fn(),
        clearRecentItems: vi.fn(),
    }),
}));

const OWN_SCOPE: ScopeDefinition = { key: "h", label: "My histories", providerId: "histories" };
const SHARED_SCOPE: ScopeDefinition = {
    key: "hs",
    label: "Shared histories",
    providerId: "histories",
    variant: "shared",
};
const PUBLISHED_SCOPE: ScopeDefinition = {
    key: "hp",
    label: "Public histories",
    providerId: "histories",
    variant: "published",
};
const ARCHIVED_SCOPE: ScopeDefinition = {
    key: "ha",
    label: "Archived histories",
    providerId: "histories",
    variant: "archived",
};

interface HistoryFields {
    annotation?: string | null;
    archived?: boolean;
    count?: number;
    owner?: string;
    username?: string;
}

function history(id: string, name: string, updateTime = "2026-08-30T10:00:00", extra: HistoryFields = {}) {
    return {
        id,
        name,
        model_class: "History",
        update_time: updateTime,
        annotation: null,
        count: 3,
        tags: [],
        archived: false,
        ...extra,
    };
}

/** Own histories, as `view=summary` serializes them: no `username` field */
const RNA = history("h1", "RNA-seq analysis", "2026-08-30T10:00:00");
const VARIANTS = history("h2", "Variant calling", "2026-08-31T10:00:00", { annotation: "exome trio" });
const REMOTE_ONLY = history("h3", "Zebrafish screen", "2026-08-29T10:00:00");

/** Listed histories always carry the owner's username */
const SHARED = history("h4", "Shared alignment", "2026-08-28T10:00:00", {
    username: "colleague",
    owner: "colleague",
});
const PUBLISHED = history("h5", "Public metagenomics", "2026-08-27T10:00:00", {
    username: "stranger",
    owner: "stranger",
});
const ARCHIVED = history("h6", "Archived assembly", "2026-08-26T10:00:00", { archived: true });

function matching(entries: ReturnType<typeof history>[], search: string) {
    const query = search.trim().toLowerCase();
    return query ? entries.filter((entry) => entry.name.toLowerCase().includes(query)) : entries;
}

function mockHistoriesApi() {
    // `getHistoryList(offset, limit, queryString)` — the palette only ever sends
    // the `name-contains` query string built from the typed text.
    getHistoryList.mockImplementation(async (_offset: number, _limit: number | null, queryString = "") => {
        const search = decodeURIComponent(queryString.split("qv=")[1] ?? "");
        return search ? matching([RNA, VARIANTS, REMOTE_ONLY], search) : [RNA, VARIANTS];
    });
    getSharedHistories.mockImplementation(async ({ search = "" }: { search?: string } = {}) => ({
        data: matching([SHARED], search),
        total: 1,
    }));
    getPublishedHistories.mockImplementation(async ({ search = "" }: { search?: string } = {}) => ({
        data: matching([PUBLISHED], search),
        total: 1,
    }));
    getArchivedHistories.mockImplementation(async ({ search = "" }: { search?: string } = {}) => ({
        data: matching([ARCHIVED], search),
        total: 1,
    }));
}

function makeCtx(isAnonymous = false): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAdmin: false, isAnonymous };
}

function signIn(username = "me") {
    const userStore = useUserStore();
    userStore.currentUser = { id: "user-1", email: "me@example.org", username, isAnonymous: false } as never;
}

async function scopedSections(scope: ScopeDefinition, query = "") {
    return (await historiesProvider.searchScoped?.(scope, query, makeCtx())) ?? [];
}

describe("historiesProvider", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        recent = [];
        vi.clearAllMocks();
        mockHistoriesApi();
        signIn();
    });

    it("shows recent and latest sections for an empty `h:` query", async () => {
        recent = [{ type: "history", id: "h1", name: "RNA-seq analysis", to: "/histories/view?id=h1" }];
        // the recent row resolves against the store, so it must be hydrated first
        await useHistoryStore().loadHistories(false);

        const sections = await scopedSections(OWN_SCOPE);

        expect(sections.map((s) => s.title)).toEqual(["Recent", "Latest"]);
        expect(sections[0]?.items.map((i) => i.title)).toEqual(["RNA-seq analysis"]);
        // latest first, so the newer "Variant calling" leads
        expect(sections[1]?.items.map((i) => i.title)).toEqual(["Variant calling", "RNA-seq analysis"]);
    });

    it("opens the history view on enter and offers set-as-current for own histories", async () => {
        const [item] = (await scopedSections(OWN_SCOPE)).at(-1)?.items ?? [];

        expect(item?.to).toBe("/histories/view?id=h2");
        expect(item?.secondaryAction?.label).toBe("Set as current");
        // the annotation wins over the bare item count
        expect(item?.subtitle).toContain("exome trio");
        expect(item?.subtitle).toContain("updated");
        expect(item?.subtitle).not.toContain("by ");
    });

    it("falls back to the item count when a history has no annotation", async () => {
        const sections = await scopedSections(OWN_SCOPE, "rna");

        expect(sections.at(-1)?.items[0]?.subtitle).toContain("3 items");
    });

    it("switches the current history through the store on shift+enter", async () => {
        setCurrentHistoryOnServer.mockResolvedValue({ id: "h2", name: "Variant calling", model_class: "History" });
        const [item] = (await scopedSections(OWN_SCOPE)).at(-1)?.items ?? [];

        item?.secondaryAction?.run?.(makeCtx());
        await Promise.resolve();

        expect(setCurrentHistoryOnServer).toHaveBeenCalledWith("h2");
    });

    it("marks the current history and drops its set-as-current action", async () => {
        const historyStore = useHistoryStore();
        await historyStore.loadHistories(false);
        historyStore.setCurrentHistoryId("h2");

        const [item] = (await scopedSections(OWN_SCOPE)).at(-1)?.items ?? [];

        expect(item?.subtitle).toContain("(current)");
        expect(item?.secondaryAction).toBeUndefined();
    });

    it("names the owner and hides set-as-current for histories of other users", async () => {
        const sections = await scopedSections(PUBLISHED_SCOPE);
        const [item] = sections.at(-1)?.items ?? [];

        expect(sections.map((s) => s.title)).toEqual(["Latest"]);
        expect(item?.title).toBe("Public metagenomics");
        expect(item?.subtitle).toContain("by stranger");
        expect(item?.secondaryAction).toBeUndefined();
    });

    it("keeps set-as-current for a listed history the current user owns", async () => {
        signIn("colleague");

        const [item] = (await scopedSections(SHARED_SCOPE)).at(-1)?.items ?? [];

        expect(item?.secondaryAction?.label).toBe("Set as current");
        expect(item?.subtitle).not.toContain("by colleague");
    });

    it("reads the shared listing for the `hs:` scope", async () => {
        const sections = await scopedSections(SHARED_SCOPE, "alignment");

        expect(sections.map((s) => s.title)).toEqual(["Shared histories"]);
        expect(sections[0]?.items.map((i) => i.title)).toEqual(["Shared alignment"]);
        expect(getSharedHistories).toHaveBeenCalled();
        expect(getPublishedHistories).not.toHaveBeenCalled();
    });

    it("reads the archived listing for `ha:`, which is owned by definition", async () => {
        const sections = await scopedSections(ARCHIVED_SCOPE);
        const [item] = sections.at(-1)?.items ?? [];

        expect(sections.map((s) => s.title)).toEqual(["Latest"]);
        expect(getArchivedHistories).toHaveBeenCalled();
        expect(item?.title).toBe("Archived assembly");
        expect(item?.secondaryAction?.label).toBe("Set as current");
    });

    it("filters the hydrated cache locally, without another backend request", async () => {
        await scopedSections(OWN_SCOPE);
        const callsAfterHydration = getHistoryList.mock.calls.length;

        const sections = await scopedSections(OWN_SCOPE, "variant");

        expect(sections.at(-1)?.items.map((i) => i.title)).toEqual(["Variant calling"]);
        // "Histories" replaces "Latest" once a query narrows the section
        expect(sections.at(-1)?.title).toBe("Histories");
        expect(getHistoryList.mock.calls.length).toBe(callsAfterHydration);
    });

    it("stays local for a single character", async () => {
        await scopedSections(OWN_SCOPE);
        const callsAfterHydration = getHistoryList.mock.calls.length;

        await scopedSections(OWN_SCOPE, "z");

        expect(getHistoryList.mock.calls.length).toBe(callsAfterHydration);
    });

    it("queries the backend and merges the matches an incomplete cache is missing", async () => {
        const historyStore = useHistoryStore();
        await historyStore.loadHistories(false);
        // the app paginated the own list itself, so the cache is a partial page
        historyStore.totalHistoryCount = 42;

        const sections = await scopedSections(OWN_SCOPE, "zebrafish");

        expect(sections.at(-1)?.items.map((i) => i.title)).toEqual(["Zebrafish screen"]);
        expect(getHistoryList.mock.calls.some(([, , queryString]) => queryString?.includes("zebrafish"))).toBe(true);
    });

    it("queries a listing whose cache is a full page", async () => {
        const page = Array.from({ length: 25 }, (_, index) =>
            history(`filler-${index}`, `Filler ${index}`, "2026-08-01T10:00:00", { username: "colleague" }),
        );
        getSharedHistories.mockImplementation(async ({ search = "" }: { search?: string } = {}) => ({
            data: search ? [SHARED] : page,
            total: 26,
        }));

        const sections = await scopedSections(SHARED_SCOPE, "alignment");

        expect(sections.at(-1)?.items.map((i) => i.title)).toEqual(["Shared alignment"]);
        expect(getSharedHistories.mock.calls.some(([options]) => options?.search === "alignment")).toBe(true);
    });

    it("keeps rendering the cache when a fetch fails", async () => {
        const historyStore = useHistoryStore();
        await historyStore.loadHistories(false);
        historyStore.totalHistoryCount = 42;
        getHistoryList.mockRejectedValue(new Error("boom"));

        const sections = await scopedSections(OWN_SCOPE, "variant");

        expect(sections.at(-1)?.items.map((i) => i.title)).toEqual(["Variant calling"]);
    });

    it("falls back to the remembered name for histories missing from the store", async () => {
        recent = [{ type: "history", id: "h9", name: "Forgotten history" }];

        const [item] = (await scopedSections(SHARED_SCOPE)).find((s) => s.id === "recent")?.items ?? [];

        expect(item?.title).toBe("Forgotten history");
        expect(item?.to).toBe("/histories/view?id=h9");
        expect(item?.secondaryAction).toBeUndefined();
    });

    it("keeps the same history addressable in several sections", async () => {
        recent = [{ type: "history", id: "h2", name: "Variant calling" }];

        const sections = await scopedSections(OWN_SCOPE);
        const ids = sections.flatMap((s) => s.items.map((i) => i.id));

        expect(new Set(ids).size).toBe(ids.length);
        expect(ids).toContain("histories:recent:h2");
        expect(ids).toContain("histories:my:h2");
    });

    it("stays out of the unscoped fan-out for short queries and anonymous users", async () => {
        expect(await historiesProvider.search("v", makeCtx())).toEqual([]);
        expect(await historiesProvider.search("variant", makeCtx(true))).toEqual([]);
        expect(getHistoryList).not.toHaveBeenCalled();
    });

    it("filters the cache in the unscoped fan-out and never fetches there", async () => {
        // nothing cached yet: the fan-out contributes nothing rather than fetching
        expect(await historiesProvider.search("variant", makeCtx())).toEqual([]);
        expect(getHistoryList).not.toHaveBeenCalled();

        await useHistoryStore().loadHistories(false);
        const callsAfterHydration = getHistoryList.mock.calls.length;

        const items = await historiesProvider.search("variant", makeCtx());

        expect(items.map((i) => i.title)).toEqual(["Variant calling"]);
        expect(getHistoryList.mock.calls.length).toBe(callsAfterHydration);
    });

    it("lists remembered histories for an empty root query", async () => {
        recent = [{ type: "history", id: "h1", name: "RNA-seq analysis" }];

        expect(historiesProvider.emptyQueryItems?.(makeCtx())?.map((i) => i.title)).toEqual(["RNA-seq analysis"]);
        expect(historiesProvider.emptyQueryItems?.(makeCtx(true))).toEqual([]);
    });
});

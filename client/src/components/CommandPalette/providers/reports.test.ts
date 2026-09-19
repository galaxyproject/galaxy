import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadPages, type LoadPagesOptions, type PageSummary } from "@/api/pages";
import { useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { usePageStore } from "@/stores/pageStore";
import { useUserStore } from "@/stores/userStore";

import type { PaletteContext } from "../types";
import { PaletteFetchError } from "./errors";
import { resetListRefreshTracking } from "./refresh";
import { reportsProvider } from "./reports";
import { findScope, type ScopeDefinition } from "./scopes";

vi.mock("@/api/pages", () => ({
    loadPages: vi.fn(),
}));

function makeCtx(overrides: Partial<PaletteContext> = {}): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAdmin: false, isAnonymous: false, ...overrides };
}

function mockPage(id: string, overrides: Partial<PageSummary> = {}): PageSummary {
    return {
        id,
        title: `Page ${id}`,
        slug: `page-${id}`,
        update_time: "2026-08-30T10:00:00",
        username: "owner",
        ...overrides,
    } as PageSummary;
}

function mockPages(pages: PageSummary[]) {
    vi.mocked(loadPages).mockResolvedValue({ data: pages, totalMatches: pages.length });
}

/** Signed in as "me"; `mockPage` hands its pages to "owner" unless told otherwise */
function signIn(username = "me") {
    useUserStore().currentUser = {
        id: "user-1",
        email: "me@example.org",
        username,
        isAnonymous: false,
    } as never;
}

function scope(key: string): ScopeDefinition {
    const found = findScope(key);
    if (!found) {
        throw new Error(`unknown scope ${key}`);
    }
    return found;
}

describe("reportsProvider", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.clearAllMocks();
        resetListRefreshTracking();
        localStorage.clear();
        useRecentPaletteItems().clearRecentItems();
        signIn();
    });

    describe("searchScoped", () => {
        it("fetches own pages once and maps them to items", async () => {
            mockPages([mockPage("a")]);

            const sections = (await reportsProvider.searchScoped?.(scope("r"), "", makeCtx())) ?? [];

            expect(loadPages).toHaveBeenCalledWith(
                expect.objectContaining({ showOwn: true, showShared: false, showPublished: false }),
            );
            expect(sections.map((section) => section.id)).toEqual(["latest"]);
            const item = sections[0]?.items[0];
            expect(item?.id).toBe("pages:a");
            expect(item?.title).toBe("Page a");
            expect(item?.subtitle).toBe("page-a · Aug 30, 2026");
            expect(item?.to).toBe("/published/page?id=a");
            expect(item?.secondaryAction).toEqual({ label: "Edit content", to: "/pages/editor?id=a" });
        });

        it("requests published pages for the rp scope and offers no edit action", async () => {
            mockPages([mockPage("p1")]);

            const sections = (await reportsProvider.searchScoped?.(scope("rp"), "", makeCtx())) ?? [];

            expect(loadPages).toHaveBeenCalledWith(
                expect.objectContaining({ showOwn: false, showShared: true, showPublished: true }),
            );
            expect(sections[0]?.id).toBe("published");
            expect(sections[0]?.items[0]?.to).toBe("/published/page?id=p1");
            expect(sections[0]?.items[0]?.secondaryAction).toBeUndefined();
        });

        it("renders from the store cache without a request when it can answer", async () => {
            mockPages([mockPage("a", { title: "Notes" }), mockPage("b", { title: "Other" })]);
            // hydrate through the palette, the way opening the scope does
            await reportsProvider.searchScoped?.(scope("r"), "", makeCtx());
            vi.mocked(loadPages).mockClear();

            const sections = (await reportsProvider.searchScoped?.(scope("r"), "Notes", makeCtx())) ?? [];

            expect(loadPages).not.toHaveBeenCalled();
            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:a"]);
            expect(sections[0]?.title).toBe("My reports");
        });

        it("queries the backend when the cache holds too few matches", async () => {
            const pageStore = usePageStore();
            mockPages([mockPage("a", { title: "Notes" })]);
            await pageStore.fetchPages("my", { search: "seed" });
            vi.mocked(loadPages).mockClear();
            mockPages([mockPage("z", { title: "Notes zulu" })]);

            const sections = (await reportsProvider.searchScoped?.(scope("r"), "Notes", makeCtx())) ?? [];

            expect(loadPages).toHaveBeenCalledWith(expect.objectContaining({ search: "Notes" }));
            expect(sections[0]?.items.map((item) => item.id)).toEqual(expect.arrayContaining(["pages:a", "pages:z"]));
        });

        it("lists remembered pages in a Recent section, without repeating them below", async () => {
            useRecentPaletteItems().addRecentItem({ type: "page", id: "a", name: "Page a" });
            mockPages([mockPage("a"), mockPage("b")]);

            const sections = (await reportsProvider.searchScoped?.(scope("r"), "", makeCtx())) ?? [];

            expect(sections.map((section) => section.title)).toEqual(["Recent", "Latest"]);
            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:a"]);
            expect(sections[1]?.items.map((item) => item.id)).toEqual(["pages:b"]);
        });

        it("keeps the palette recents out of the published scope", async () => {
            // the MRU is one list per entity type, so a page opened through
            // `r:` must not leak into the published scope
            useRecentPaletteItems().addRecentItem({ type: "page", id: "a", name: "Page a" });
            mockPages([mockPage("b")]);

            const sections = (await reportsProvider.searchScoped?.(scope("rp"), "", makeCtx())) ?? [];

            expect(sections.map((section) => section.id)).toEqual(["published"]);
            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:b"]);
        });

        it("sorts the list section by update time, newest first", async () => {
            mockPages([
                mockPage("old", { update_time: "2026-01-01T10:00:00" }),
                mockPage("new", { update_time: "2026-08-30T10:00:00" }),
            ]);

            const sections = (await reportsProvider.searchScoped?.(scope("r"), "", makeCtx())) ?? [];

            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:new", "pages:old"]);
        });

        it("returns nothing for the own scope of an anonymous user", async () => {
            const sections =
                (await reportsProvider.searchScoped?.(scope("r"), "", makeCtx({ isAnonymous: true }))) ?? [];

            expect(sections).toEqual([]);
            expect(loadPages).not.toHaveBeenCalled();
        });

        it("serves the published scope to anonymous users", async () => {
            mockPages([mockPage("p1")]);

            const sections =
                (await reportsProvider.searchScoped?.(scope("rp"), "", makeCtx({ isAnonymous: true }))) ?? [];

            expect(loadPages).toHaveBeenCalledWith(expect.objectContaining({ showOwn: false, showPublished: true }));
            expect(sections.map((section) => section.id)).toEqual(["published"]);
            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:p1"]);
        });

        it("keeps querying the backend after a search that found nothing", async () => {
            const pageStore = usePageStore();
            // the first thing this session ever fetched was a fruitless search:
            // it says nothing about the rest of the list
            mockPages([]);
            await pageStore.fetchPages("my", { search: "zzz" });
            vi.mocked(loadPages).mockClear();
            mockPages([mockPage("a", { title: "Notes" })]);

            const sections = (await reportsProvider.searchScoped?.(scope("r"), "Notes", makeCtx())) ?? [];

            expect(loadPages).toHaveBeenCalledWith(expect.objectContaining({ search: "Notes" }));
            expect(sections.at(-1)?.items.map((item) => item.id)).toEqual(["pages:a"]);
        });

        it("refreshes a complete cache in the background once it goes stale", async () => {
            mockPages([mockPage("a")]);
            await reportsProvider.searchScoped?.(scope("r"), "", makeCtx());
            expect(loadPages).toHaveBeenCalledTimes(1);

            // a later palette session, past the refresh interval
            resetListRefreshTracking();
            const sections = (await reportsProvider.searchScoped?.(scope("r"), "", makeCtx())) ?? [];

            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:a"]);
            expect(loadPages).toHaveBeenCalledTimes(2);
        });

        it("reports a scope whose very first fetch failed", async () => {
            vi.mocked(loadPages).mockRejectedValue(new Error("boom"));

            // nothing is cached, so "no results" would be a lie
            await expect(reportsProvider.searchScoped?.(scope("r"), "", makeCtx())).rejects.toBeInstanceOf(
                PaletteFetchError,
            );
        });

        it("keeps serving the cache when the request fails", async () => {
            const pageStore = usePageStore();
            pageStore.savePages("my", [mockPage("a")]);
            vi.mocked(loadPages).mockRejectedValue(new Error("boom"));

            const sections = (await reportsProvider.searchScoped?.(scope("r"), "", makeCtx())) ?? [];

            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:a"]);
        });
    });

    describe("search", () => {
        it("filters the cached own pages without fetching them", async () => {
            mockPages([mockPage("a", { title: "Notes" })]);
            await usePageStore().fetchPages("my");
            vi.mocked(loadPages).mockClear();
            mockPages([]);

            const items = await reportsProvider.search("notes", makeCtx());

            expect(items.map((item) => item.id)).toEqual(["pages:a"]);
            // the own list is only ever fetched by the `r:` scope
            expect(loadPages).not.toHaveBeenCalledWith(expect.objectContaining({ showOwn: true }));
        });

        it("merges the published matches into the fan-out", async () => {
            mockPages([mockPage("a", { title: "Notes", username: "me" })]);
            await usePageStore().fetchPages("my");
            vi.mocked(loadPages).mockClear();
            mockPages([mockPage("z", { title: "Notes of a stranger" })]);

            const items = await reportsProvider.search("notes", makeCtx());

            expect(items.map((item) => item.id).sort()).toEqual(["pages:a", "pages:z"]);
            // one page of public rows, which the client then ranks and caps itself
            expect(loadPages).toHaveBeenCalledWith(
                expect.objectContaining({ showPublished: true, search: "notes", limit: 8 }),
            );
        });

        it("pages the published listing in the fan-out, so a match below the newest rows survives", async () => {
            // the backend orders by update time and matches loosely, and it
            // honors the requested limit, so the rows it answers with first
            // need not match the query at all
            const loose = Array.from({ length: 7 }, (_, index) =>
                mockPage(`loose-${index}`, { title: `Draft ${index}` }),
            );
            const match = mockPage("z", { title: "Notes of a stranger" });
            vi.mocked(loadPages).mockImplementation(async ({ limit }: LoadPagesOptions = {}) => {
                const data = [...loose, match].slice(0, limit);
                return { data, totalMatches: data.length };
            });

            const items = await reportsProvider.search("notes", makeCtx({ isAnonymous: true }));

            expect(items.map((item) => item.id)).toContain("pages:z");
            // a whole page is asked for, so the ranking has the match to find
            expect(loadPages).toHaveBeenCalledWith(
                expect.objectContaining({ showPublished: true, search: "notes", limit: 8 }),
            );
            // the section itself stays capped at the handful of rows it renders
            expect(items.length).toBeLessThanOrEqual(3);
        });

        it("keeps the fan-out's published hits out of the cached listing", async () => {
            mockPages([mockPage("z", { title: "Notes of a stranger" })]);

            await reportsProvider.search("notes", makeCtx({ isAnonymous: true }));

            const pageStore = usePageStore();
            // the hits answered one query, so the listing itself is still unfetched
            expect(pageStore.publishedPages).toEqual([]);
            expect(pageStore.isLoaded("published")).toBe(false);

            vi.mocked(loadPages).mockClear();
            mockPages([mockPage("p1", { title: "Public notes" })]);
            const sections = (await reportsProvider.searchScoped?.(scope("rp"), "", makeCtx())) ?? [];

            // …and `rp:` fetches a full, unfiltered listing of its own
            expect(loadPages).toHaveBeenCalledWith(expect.objectContaining({ search: "", showPublished: true }));
            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:p1"]);
        });

        it("keeps one row per page in the fan-out, preferring the user's own", async () => {
            // `mockPage` hands its pages to "owner", so only the own listing
            // proves that the page belongs to the current user
            mockPages([mockPage("a", { title: "Notes" })]);
            await usePageStore().fetchPages("my");
            vi.mocked(loadPages).mockClear();

            const items = await reportsProvider.search("notes", makeCtx());

            expect(items.map((item) => item.id)).toEqual(["pages:a"]);
            expect(items[0]?.secondaryAction).toEqual({ label: "Edit content", to: "/pages/editor?id=a" });
        });

        it("searches the published pages alone for an anonymous root query", async () => {
            mockPages([mockPage("p1", { title: "Public notes" })]);

            const items = await reportsProvider.search("notes", makeCtx({ isAnonymous: true }));

            expect(items.map((item) => item.id)).toEqual(["pages:p1"]);
            expect(loadPages).toHaveBeenCalledTimes(1);
            expect(loadPages).toHaveBeenCalledWith(expect.objectContaining({ showOwn: false, showPublished: true }));
        });

        it("keeps the cached own rows when the published search fails", async () => {
            mockPages([mockPage("a", { title: "Notes" })]);
            await usePageStore().fetchPages("my");
            vi.mocked(loadPages).mockRejectedValue(new Error("boom"));

            const items = await reportsProvider.search("notes", makeCtx());

            expect(items.map((item) => item.id)).toEqual(["pages:a"]);
        });

        it("skips single character queries", async () => {
            mockPages([mockPage("a")]);

            expect(await reportsProvider.search("n", makeCtx())).toEqual([]);
            expect(await reportsProvider.search("n", makeCtx({ isAnonymous: true }))).toEqual([]);
            expect(loadPages).not.toHaveBeenCalled();
        });
    });

    describe("emptyQueryItems", () => {
        it("lists remembered pages, enriched from the store when cached", () => {
            usePageStore().savePages("my", [mockPage("a")]);
            useRecentPaletteItems().addRecentItem({ type: "page", id: "a", name: "stale name" });
            useRecentPaletteItems().addRecentItem({
                type: "page",
                id: "b",
                name: "Uncached",
                to: "/published/page?id=b",
            });

            const items = reportsProvider.emptyQueryItems?.(makeCtx()) ?? [];

            expect(items.map((item) => item.id)).toEqual(["pages:b", "pages:a"]);
            expect(items[1]?.title).toBe("Page a");
            expect(items[1]?.subtitle).toBe("page-a · Aug 30, 2026");
            expect(items[0]?.title).toBe("Uncached");
        });

        it("offers the editor on a remembered page only when the user owns it", () => {
            usePageStore().savePages("published", [
                mockPage("mine", { username: "me" }),
                mockPage("theirs", { username: "someone-else" }),
            ]);
            useRecentPaletteItems().addRecentItem({ type: "page", id: "theirs", name: "Page theirs" });
            useRecentPaletteItems().addRecentItem({ type: "page", id: "mine", name: "Page mine" });

            const items = reportsProvider.emptyQueryItems?.(makeCtx()) ?? [];

            expect(items.map((item) => item.id)).toEqual(["pages:mine", "pages:theirs"]);
            expect(items[0]?.secondaryAction).toEqual({ label: "Edit content", to: "/pages/editor?id=mine" });
            expect(items[1]?.secondaryAction).toBeUndefined();
        });

        it("is empty for anonymous users", () => {
            useRecentPaletteItems().addRecentItem({ type: "page", id: "a", name: "Page a" });

            expect(reportsProvider.emptyQueryItems?.(makeCtx({ isAnonymous: true }))).toEqual([]);
        });
    });
});

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadPages, type PageSummary } from "@/api/pages";
import { useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { usePageStore } from "@/stores/pageStore";
import { useUserStore } from "@/stores/userStore";

import type { PaletteContext } from "../types";
import { pagesProvider } from "./pages";
import { resetListRefreshTracking } from "./refresh";
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

describe("pagesProvider", () => {
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

            const sections = (await pagesProvider.searchScoped?.(scope("p"), "", makeCtx())) ?? [];

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

        it("requests published pages for the pp scope and offers no edit action", async () => {
            mockPages([mockPage("p1")]);

            const sections = (await pagesProvider.searchScoped?.(scope("pp"), "", makeCtx())) ?? [];

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
            await pagesProvider.searchScoped?.(scope("p"), "", makeCtx());
            vi.mocked(loadPages).mockClear();

            const sections = (await pagesProvider.searchScoped?.(scope("p"), "Notes", makeCtx())) ?? [];

            expect(loadPages).not.toHaveBeenCalled();
            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:a"]);
            expect(sections[0]?.title).toBe("My pages");
        });

        it("queries the backend when the cache holds too few matches", async () => {
            const pageStore = usePageStore();
            mockPages([mockPage("a", { title: "Notes" })]);
            await pageStore.fetchPages("my", { search: "seed" });
            vi.mocked(loadPages).mockClear();
            mockPages([mockPage("z", { title: "Notes zulu" })]);

            const sections = (await pagesProvider.searchScoped?.(scope("p"), "Notes", makeCtx())) ?? [];

            expect(loadPages).toHaveBeenCalledWith(expect.objectContaining({ search: "Notes" }));
            expect(sections[0]?.items.map((item) => item.id)).toEqual(expect.arrayContaining(["pages:a", "pages:z"]));
        });

        it("lists remembered pages in a Recent section, without repeating them below", async () => {
            useRecentPaletteItems().addRecentItem({ type: "page", id: "a", name: "Page a" });
            mockPages([mockPage("a"), mockPage("b")]);

            const sections = (await pagesProvider.searchScoped?.(scope("p"), "", makeCtx())) ?? [];

            expect(sections.map((section) => section.title)).toEqual(["Recent", "Latest"]);
            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:a"]);
            expect(sections[1]?.items.map((item) => item.id)).toEqual(["pages:b"]);
        });

        it("keeps the palette recents out of the published scope", async () => {
            // the MRU is one list per entity type, so a page opened through
            // `p:` must not leak into the published scope
            useRecentPaletteItems().addRecentItem({ type: "page", id: "a", name: "Page a" });
            mockPages([mockPage("b")]);

            const sections = (await pagesProvider.searchScoped?.(scope("pp"), "", makeCtx())) ?? [];

            expect(sections.map((section) => section.id)).toEqual(["published"]);
            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:b"]);
        });

        it("sorts the list section by update time, newest first", async () => {
            mockPages([
                mockPage("old", { update_time: "2026-01-01T10:00:00" }),
                mockPage("new", { update_time: "2026-08-30T10:00:00" }),
            ]);

            const sections = (await pagesProvider.searchScoped?.(scope("p"), "", makeCtx())) ?? [];

            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:new", "pages:old"]);
        });

        it("returns nothing for anonymous users", async () => {
            const sections = (await pagesProvider.searchScoped?.(scope("p"), "", makeCtx({ isAnonymous: true }))) ?? [];

            expect(sections).toEqual([]);
            expect(loadPages).not.toHaveBeenCalled();
        });

        it("keeps querying the backend after a search that found nothing", async () => {
            const pageStore = usePageStore();
            // the first thing this session ever fetched was a fruitless search:
            // it says nothing about the rest of the list
            mockPages([]);
            await pageStore.fetchPages("my", { search: "zzz" });
            vi.mocked(loadPages).mockClear();
            mockPages([mockPage("a", { title: "Notes" })]);

            const sections = (await pagesProvider.searchScoped?.(scope("p"), "Notes", makeCtx())) ?? [];

            expect(loadPages).toHaveBeenCalledWith(expect.objectContaining({ search: "Notes" }));
            expect(sections.at(-1)?.items.map((item) => item.id)).toEqual(["pages:a"]);
        });

        it("refreshes a complete cache in the background once it goes stale", async () => {
            mockPages([mockPage("a")]);
            await pagesProvider.searchScoped?.(scope("p"), "", makeCtx());
            expect(loadPages).toHaveBeenCalledTimes(1);

            // a later palette session, past the refresh interval
            resetListRefreshTracking();
            const sections = (await pagesProvider.searchScoped?.(scope("p"), "", makeCtx())) ?? [];

            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:a"]);
            expect(loadPages).toHaveBeenCalledTimes(2);
        });

        it("keeps serving the cache when the request fails", async () => {
            const pageStore = usePageStore();
            pageStore.savePages("my", [mockPage("a")]);
            vi.mocked(loadPages).mockRejectedValue(new Error("boom"));

            const sections = (await pagesProvider.searchScoped?.(scope("p"), "", makeCtx())) ?? [];

            expect(sections[0]?.items.map((item) => item.id)).toEqual(["pages:a"]);
        });
    });

    describe("search", () => {
        it("filters the cached own pages and never fetches for a root query", async () => {
            mockPages([mockPage("a", { title: "Notes" })]);
            // nothing cached yet: the fan-out contributes nothing rather than fetching
            expect(await pagesProvider.search("notes", makeCtx())).toEqual([]);
            expect(loadPages).not.toHaveBeenCalled();

            await usePageStore().fetchPages("my");
            vi.mocked(loadPages).mockClear();

            const items = await pagesProvider.search("notes", makeCtx());

            expect(items.map((item) => item.id)).toEqual(["pages:a"]);
            expect(loadPages).not.toHaveBeenCalled();
        });

        it("skips single character and anonymous queries", async () => {
            mockPages([mockPage("a")]);

            expect(await pagesProvider.search("n", makeCtx())).toEqual([]);
            expect(await pagesProvider.search("notes", makeCtx({ isAnonymous: true }))).toEqual([]);
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

            const items = pagesProvider.emptyQueryItems?.(makeCtx()) ?? [];

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

            const items = pagesProvider.emptyQueryItems?.(makeCtx()) ?? [];

            expect(items.map((item) => item.id)).toEqual(["pages:mine", "pages:theirs"]);
            expect(items[0]?.secondaryAction).toEqual({ label: "Edit content", to: "/pages/editor?id=mine" });
            expect(items[1]?.secondaryAction).toBeUndefined();
        });

        it("is empty for anonymous users", () => {
            useRecentPaletteItems().addRecentItem({ type: "page", id: "a", name: "Page a" });

            expect(pagesProvider.emptyQueryItems?.(makeCtx({ isAnonymous: true }))).toEqual([]);
        });
    });
});

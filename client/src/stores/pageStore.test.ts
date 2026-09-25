import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadPages, type PageSummary } from "@/api/pages";
import { usePageStore } from "@/stores/pageStore";

vi.mock("@/api/pages", () => ({
    loadPages: vi.fn(),
}));

function mockPage(id: string, title = `Page ${id}`): PageSummary {
    return { id, title } as PageSummary;
}

function mockResult(pages: PageSummary[], totalMatches = pages.length) {
    return { data: pages, totalMatches };
}

describe("usePageStore", () => {
    let pageStore: ReturnType<typeof usePageStore>;

    beforeEach(() => {
        setActivePinia(createPinia());
        pageStore = usePageStore();
        vi.clearAllMocks();
    });

    describe("fetchPages", () => {
        it("requests own pages for the `my` variant and caches the result", async () => {
            vi.mocked(loadPages).mockResolvedValue(mockResult([mockPage("a"), mockPage("b")], 2));

            const pages = await pageStore.fetchPages("my");

            expect(loadPages).toHaveBeenCalledWith(
                expect.objectContaining({ showOwn: true, showShared: false, showPublished: false }),
            );
            expect(pages).toHaveLength(2);
            expect(pageStore.myPages.map((page) => page.id)).toEqual(["a", "b"]);
            expect(pageStore.getPageById("a")?.title).toBe("Page a");
            expect(pageStore.isLoaded("my")).toBe(true);
            expect(pageStore.isLoading("my")).toBe(false);
        });

        it("requests published and shared pages for the `published` variant", async () => {
            vi.mocked(loadPages).mockResolvedValue(mockResult([mockPage("p1")]));

            await pageStore.fetchPages("published");

            expect(loadPages).toHaveBeenCalledWith(
                expect.objectContaining({ showOwn: false, showShared: true, showPublished: true }),
            );
            expect(pageStore.publishedPages.map((page) => page.id)).toEqual(["p1"]);
            expect(pageStore.myPages).toEqual([]);
        });

        it("forwards search, sorting and paging options", async () => {
            vi.mocked(loadPages).mockResolvedValue(mockResult([]));

            await pageStore.fetchPages("my", {
                search: "notes",
                sortBy: "title",
                sortDesc: false,
                limit: 5,
                offset: 5,
            });

            expect(loadPages).toHaveBeenCalledWith({
                showOwn: true,
                showShared: false,
                showPublished: false,
                search: "notes",
                sortBy: "title",
                sortDesc: false,
                limit: 5,
                offset: 5,
            });
        });

        it("merges search results into the cache without duplicating entries", async () => {
            vi.mocked(loadPages).mockResolvedValueOnce(mockResult([mockPage("a"), mockPage("b")], 2));
            await pageStore.fetchPages("my");

            vi.mocked(loadPages).mockResolvedValueOnce(mockResult([mockPage("b", "Renamed b"), mockPage("c")], 2));
            await pageStore.fetchPages("my", { search: "b" });

            expect(pageStore.myPages.map((page) => page.id)).toEqual(["a", "b", "c"]);
            expect(pageStore.getPageById("b")?.title).toBe("Renamed b");
            expect(Object.keys(pageStore.summariesById)).toHaveLength(3);
        });

        it("keeps the server order of a full listing in front of previously cached pages", async () => {
            vi.mocked(loadPages).mockResolvedValueOnce(mockResult([mockPage("old")], 1));
            await pageStore.fetchPages("my", { search: "old" });

            vi.mocked(loadPages).mockResolvedValueOnce(mockResult([mockPage("new"), mockPage("older")], 3));
            await pageStore.fetchPages("my");

            expect(pageStore.myPages.map((page) => page.id)).toEqual(["new", "older", "old"]);
        });

        it("deduplicates identical concurrent requests", async () => {
            let resolvePages: (value: { data: PageSummary[]; totalMatches: number }) => void = () => undefined;
            vi.mocked(loadPages).mockReturnValue(
                new Promise((resolve) => {
                    resolvePages = resolve;
                }),
            );

            const first = pageStore.fetchPages("my");
            const second = pageStore.fetchPages("my");

            expect(loadPages).toHaveBeenCalledTimes(1);
            expect(pageStore.isLoading("my")).toBe(true);

            resolvePages(mockResult([mockPage("a")]));
            const [firstPages, secondPages] = await Promise.all([first, second]);

            expect(firstPages).toEqual(secondPages);
            expect(loadPages).toHaveBeenCalledTimes(1);
            expect(pageStore.isLoading("my")).toBe(false);
        });

        it("issues separate requests for different queries", async () => {
            vi.mocked(loadPages).mockResolvedValue(mockResult([]));

            await Promise.all([pageStore.fetchPages("my"), pageStore.fetchPages("my", { search: "notes" })]);

            expect(loadPages).toHaveBeenCalledTimes(2);
        });

        it("keeps one-off search results out of the canonical listing", async () => {
            vi.mocked(loadPages).mockResolvedValueOnce(mockResult([mockPage("search-hit")], 1));

            await pageStore.fetchPages("my", { search: "needle", record: false });

            expect(pageStore.getPageById("search-hit")).toBeDefined();
            expect(pageStore.myPages).toEqual([]);
            expect(pageStore.isLoaded("my")).toBe(false);

            vi.mocked(loadPages).mockResolvedValueOnce(mockResult([mockPage("canonical-hit")], 5));
            const canonical = await pageStore.fetchPagesOnce("my");

            expect(loadPages).toHaveBeenCalledTimes(2);
            expect(canonical.map((page) => page.id)).toEqual(["canonical-hit"]);
            expect(pageStore.myPages.map((page) => page.id)).toEqual(["canonical-hit"]);
            expect(pageStore.getPageById("search-hit")).toBeDefined();
        });

        it("resets the loading flag and rethrows when the request fails", async () => {
            vi.mocked(loadPages).mockRejectedValue(new Error("boom"));

            await expect(pageStore.fetchPages("my")).rejects.toThrow("boom");

            expect(pageStore.isLoading("my")).toBe(false);
            expect(pageStore.isLoaded("my")).toBe(false);
        });
    });

    describe("fetchPagesOnce", () => {
        it("fetches only the first time and serves the cache afterwards", async () => {
            vi.mocked(loadPages).mockResolvedValue(mockResult([mockPage("a")], 1));

            const first = await pageStore.fetchPagesOnce("my");
            const second = await pageStore.fetchPagesOnce("my");

            expect(loadPages).toHaveBeenCalledTimes(1);
            expect(first.map((page) => page.id)).toEqual(["a"]);
            expect(second.map((page) => page.id)).toEqual(["a"]);
        });

        it("fetches each variant separately", async () => {
            vi.mocked(loadPages).mockResolvedValue(mockResult([mockPage("a")], 1));

            await pageStore.fetchPagesOnce("my");
            await pageStore.fetchPagesOnce("published");

            expect(loadPages).toHaveBeenCalledTimes(2);
        });
    });

    describe("isComplete", () => {
        it("is false until a full listing is cached", async () => {
            expect(pageStore.isComplete("my")).toBe(false);

            vi.mocked(loadPages).mockResolvedValueOnce(mockResult([mockPage("a")], 5));
            await pageStore.fetchPages("my");
            expect(pageStore.isComplete("my")).toBe(false);

            vi.mocked(loadPages).mockResolvedValueOnce(mockResult([mockPage("a"), mockPage("b")], 2));
            await pageStore.fetchPages("my");
            expect(pageStore.isComplete("my")).toBe(true);
        });

        it("stays false after a search that found nothing", async () => {
            vi.mocked(loadPages).mockResolvedValue(mockResult([], 0));

            await pageStore.fetchPages("my", { search: "nothing matches this" });

            // the variant counts as loaded, but a filtered fetch never reports
            // how many pages exist, so completeness cannot follow from it
            expect(pageStore.isLoaded("my")).toBe(true);
            expect(pageStore.isComplete("my")).toBe(false);
        });

        it("is true for an unfiltered listing that came back empty", async () => {
            vi.mocked(loadPages).mockResolvedValue(mockResult([], 0));

            await pageStore.fetchPages("my");

            expect(pageStore.isComplete("my")).toBe(true);
        });
    });

    describe("savePages and removePage", () => {
        it("saves pages without a request", () => {
            pageStore.savePages("my", [mockPage("a"), mockPage("b")]);

            expect(loadPages).not.toHaveBeenCalled();
            expect(pageStore.myPages.map((page) => page.id)).toEqual(["a", "b"]);
        });

        it("removes a page from the cache and from all variant lists", () => {
            pageStore.savePages("my", [mockPage("a"), mockPage("b")]);
            pageStore.savePages("published", [mockPage("a")]);

            pageStore.removePage("a");

            expect(pageStore.getPageById("a")).toBeUndefined();
            expect(pageStore.myPages.map((page) => page.id)).toEqual(["b"]);
            expect(pageStore.publishedPages).toEqual([]);
        });
    });
});

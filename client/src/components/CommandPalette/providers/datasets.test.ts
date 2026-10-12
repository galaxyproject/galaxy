import { getFakeHistorySummary } from "@tests/test-data";
import { getFakeCollectionSummary } from "@tests/test-data/collections";
import { getFakeDatasetSummary } from "@tests/test-data/datasets";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";

import type { HistoryItemSummary } from "@/api";
import type * as datasetsApi from "@/api/datasets";
import { loadDatasets, type LoadDatasetsOptions } from "@/api/datasets";
import type { RecentPaletteItem } from "@/composables/useRecentPaletteItems";
import { useDatasetListStore } from "@/stores/datasetListStore";
import { useHistoryStore } from "@/stores/historyStore";

import { makeCtx, renderedSections } from "../test-utils";
import { datasetsProvider } from "./datasets";
import { resetListRefreshTracking } from "./refresh";
import type { ScopeDefinition } from "./scopes";

vi.mock("@/api/datasets", async (importOriginal) => ({
    ...(await importOriginal<typeof datasetsApi>()),
    loadDatasets: vi.fn(),
}));

const recentEntries: RecentPaletteItem[] = [];

vi.mock("@/composables/useRecentPaletteItems", () => ({
    useRecentPaletteItems: () => ({
        recentItems: (type: string) => (type === "dataset" ? recentEntries : []),
        addRecentItem: vi.fn(),
        clearRecentItems: vi.fn(),
    }),
}));

const DATASETS_SCOPE: ScopeDefinition = { key: "d", label: "Datasets", providerId: "datasets" };
const searchScopedDatasets = datasetsProvider.searchScoped;
if (!searchScopedDatasets) {
    throw new Error("The datasets provider must support scoped search");
}

function makeDataset(id: string, name: string, updateTime: string) {
    return getFakeDatasetSummary({
        id,
        name,
        extension: "txt",
        state: "ok",
        history_id: "history_1",
        update_time: updateTime,
        create_time: updateTime,
    });
}

const ALPHA = makeDataset("d1", "alpha reads", "2026-01-03T00:00:00");
const BETA = makeDataset("d2", "beta reads", "2026-01-05T00:00:00");

/** Serves the unfiltered "latest" list, and name-filters for search fetches */
function mockLoadDatasets(all: HistoryItemSummary[] = [ALPHA, BETA]) {
    vi.mocked(loadDatasets).mockImplementation(async ({ search }: LoadDatasetsOptions) => {
        const data = search ? all.filter((dataset) => dataset.name?.includes(search)) : all;
        return { data, totalMatches: data.length };
    });
}

describe("datasetsProvider", () => {
    beforeEach(() => {
        const pinia = createPinia();
        setActivePinia(pinia);
        onTestFinished(() => disposePinia(pinia));
        vi.mocked(loadDatasets).mockReset();
        resetListRefreshTracking();
        recentEntries.length = 0;
    });

    it("lists recent and latest datasets for an empty scoped query", async () => {
        mockLoadDatasets();
        recentEntries.push({ type: "dataset", id: "d1", name: "alpha reads", to: "/datasets/d1/preview" });

        const sections = await searchScopedDatasets(DATASETS_SCOPE, "", makeCtx());
        expect(sections.map((s) => s.id)).toEqual(["recent", "latest"]);
        expect(sections[0]?.items.map((i) => i.id)).toEqual(["datasets:d1"]);
        // latest is update_time descending and skips what "Recent" already shows
        expect(sections[1]?.items.map((i) => i.id)).toEqual(["datasets:d2"]);
    });

    it("maps a dataset to a preview link with extension and state", async () => {
        mockLoadDatasets();

        const sections = await searchScopedDatasets(DATASETS_SCOPE, "alpha", makeCtx());
        const items = sections.find((section) => section.id === "results")?.items ?? [];

        expect(items).toHaveLength(1);
        expect(items[0]?.id).toBe("datasets:d1");
        expect(items[0]?.title).toBe("alpha reads");
        expect(items[0]?.subtitle).toBe("txt · ok");
        expect(items[0]?.to).toBe("/datasets/d1/preview");
    });

    it("appends the owning history name when it is already cached", async () => {
        mockLoadDatasets();
        useHistoryStore().setHistory(getFakeHistorySummary({ id: "history_1", name: "My analysis" }));

        const sections = await searchScopedDatasets(DATASETS_SCOPE, "alpha", makeCtx());

        expect(sections.at(-1)?.items[0]?.subtitle).toBe("txt · ok · My analysis");
    });

    it("answers a scoped query from the store cache without a second request", async () => {
        mockLoadDatasets();
        // hydrate through the palette, the way opening the scope does
        await searchScopedDatasets(DATASETS_SCOPE, "", makeCtx());
        vi.mocked(loadDatasets).mockClear();

        const sections = await searchScopedDatasets(DATASETS_SCOPE, "beta", makeCtx());

        expect(sections.at(-1)?.items.map((i) => i.id)).toEqual(["datasets:d2"]);
        // the unfiltered fetch reported two matches and the cache holds both,
        // so a backend search could not add anything
        expect(loadDatasets).not.toHaveBeenCalled();
    });

    it("keeps searching locally instead of per keystroke once the cache is complete", async () => {
        mockLoadDatasets();
        await searchScopedDatasets(DATASETS_SCOPE, "", makeCtx());
        vi.mocked(loadDatasets).mockClear();

        // queries without a single local match: the complete cache answers them
        await searchScopedDatasets(DATASETS_SCOPE, "zz", makeCtx());
        const sections = renderedSections(await searchScopedDatasets(DATASETS_SCOPE, "zzz", makeCtx()));

        expect(sections).toEqual([]);
        expect(loadDatasets).not.toHaveBeenCalled();
    });

    it("treats the cache as complete when the backend total also counts collections", async () => {
        const collection = getFakeCollectionSummary({
            id: "c1",
            name: "paired list",
            history_content_type: "dataset_collection",
            update_time: "2026-01-04T00:00:00",
        });
        mockLoadDatasets([ALPHA, collection, BETA]);
        await searchScopedDatasets(DATASETS_SCOPE, "", makeCtx());
        vi.mocked(loadDatasets).mockClear();

        const sections = renderedSections(await searchScopedDatasets(DATASETS_SCOPE, "zz", makeCtx()));

        expect(sections).toEqual([]);
        expect(loadDatasets).not.toHaveBeenCalled();
    });

    it("refreshes the cached datasets in the background once they go stale", async () => {
        mockLoadDatasets();
        await searchScopedDatasets(DATASETS_SCOPE, "", makeCtx());
        vi.mocked(loadDatasets).mockClear();

        // a later palette session, past the refresh interval
        resetListRefreshTracking();
        const sections = renderedSections(await searchScopedDatasets(DATASETS_SCOPE, "", makeCtx()));

        expect(sections[0]?.items.map((i) => i.id)).toEqual(["datasets:d2", "datasets:d1"]);
        expect(loadDatasets).toHaveBeenCalledTimes(1);
    });

    it("merges backend matches missing from the cache into the store", async () => {
        const GAMMA = makeDataset("d3", "gamma reads", "2026-01-01T00:00:00");
        mockLoadDatasets([ALPHA, BETA, GAMMA]);
        // the first page does not cover everything the backend reports, so the
        // cache cannot answer a query on its own
        vi.mocked(loadDatasets).mockImplementationOnce(async () => ({ data: [ALPHA, BETA], totalMatches: 30 }));

        const sections = await searchScopedDatasets(DATASETS_SCOPE, "gamma", makeCtx());

        expect(sections.at(-1)?.items.map((i) => i.id)).toEqual(["datasets:d3"]);
        expect(useDatasetListStore().getDatasetSummary("d3")).toBeDefined();
    });

    it("filters the cache in the unscoped fan-out and never fetches there", async () => {
        mockLoadDatasets();
        // nothing cached yet: the fan-out contributes nothing rather than fetching
        expect(await datasetsProvider.search("beta", makeCtx())).toEqual([]);

        await useDatasetListStore().ensureLatestLoaded();
        vi.mocked(loadDatasets).mockClear();

        const items = await datasetsProvider.search("beta", makeCtx());

        expect(items.map((i) => i.id)).toEqual(["datasets:d2"]);
        expect(loadDatasets).not.toHaveBeenCalled();
    });
});

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadVisualizations, type VisualizationSummary } from "@/api/visualizations";
import { useVisualizationStore } from "@/stores/visualizationStore";

vi.mock("@/api/visualizations", () => ({
    loadVisualizations: vi.fn(),
}));

function mockVisualization(id: string, title: string): VisualizationSummary {
    return {
        id,
        title,
        type: "nvd3_bar",
        annotation: null,
        create_time: "2026-01-01T00:00:00",
        update_time: "2026-01-02T00:00:00",
        deleted: false,
        importable: false,
        published: false,
        tags: [],
        username: "test-user",
    } as VisualizationSummary;
}

describe("useVisualizationStore", () => {
    let store: ReturnType<typeof useVisualizationStore>;

    beforeEach(() => {
        setActivePinia(createPinia());
        store = useVisualizationStore();
        vi.mocked(loadVisualizations).mockReset();
    });

    it("stores summaries by id and keeps the returned order per variant", async () => {
        const data = [mockVisualization("viz-2", "Second"), mockVisualization("viz-1", "First")];
        vi.mocked(loadVisualizations).mockResolvedValue({ data, totalMatches: 2 });

        await store.fetchVisualizations("my");

        expect(store.visualizationIdsByVariant.my).toEqual(["viz-2", "viz-1"]);
        expect(store.getVisualizations("my").map((viz) => viz.title)).toEqual(["Second", "First"]);
        expect(store.getVisualizationSummary("viz-1")?.title).toBe("First");
        expect(store.totalMatchesByVariant.my).toBe(2);
        expect(store.hasLoadedVariant("my")).toBe(true);
        expect(store.hasLoadedVariant("shared")).toBe(false);
    });

    it("sends the explicit scope triplet of the requested variant", async () => {
        vi.mocked(loadVisualizations).mockResolvedValue({ data: [], totalMatches: 0 });

        await store.fetchVisualizations("published", { limit: 5 });

        expect(loadVisualizations).toHaveBeenCalledWith({
            showOwn: false,
            showShared: false,
            showPublished: true,
            sortBy: "update_time",
            sortDesc: true,
            limit: 5,
            search: "",
        });
    });

    it("merges repeated fetches into a single cache entry per id", async () => {
        vi.mocked(loadVisualizations).mockResolvedValueOnce({
            data: [mockVisualization("viz-1", "First"), mockVisualization("viz-2", "Second")],
            totalMatches: 2,
        });
        vi.mocked(loadVisualizations).mockResolvedValueOnce({
            data: [mockVisualization("viz-2", "Second renamed")],
            totalMatches: 1,
        });

        await store.fetchVisualizations("my");
        await store.fetchVisualizations("shared");

        expect(Object.keys(store.storedVisualizations).sort()).toEqual(["viz-1", "viz-2"]);
        expect(store.getVisualizationSummary("viz-2")?.title).toBe("Second renamed");
        expect(store.visualizationIdsByVariant.shared).toEqual(["viz-2"]);
    });

    it("does not redefine the variant list for a filtered fetch", async () => {
        vi.mocked(loadVisualizations).mockResolvedValueOnce({
            data: [mockVisualization("viz-1", "First")],
            totalMatches: 1,
        });
        vi.mocked(loadVisualizations).mockResolvedValueOnce({
            data: [mockVisualization("viz-9", "Ninth")],
            totalMatches: 1,
        });

        await store.fetchVisualizations("my");
        await store.fetchVisualizations("my", { search: "ninth" });

        expect(store.visualizationIdsByVariant.my).toEqual(["viz-1"]);
        expect(store.getVisualizationSummary("viz-9")?.title).toBe("Ninth");
    });

    it("fetches a variant only once via ensureVariantLoaded", async () => {
        vi.mocked(loadVisualizations).mockResolvedValue({
            data: [mockVisualization("viz-1", "First")],
            totalMatches: 1,
        });

        const first = await store.ensureVariantLoaded("my");
        const second = await store.ensureVariantLoaded("my");

        expect(loadVisualizations).toHaveBeenCalledTimes(1);
        expect(first).toEqual(second);
        expect(first.map((viz) => viz.id)).toEqual(["viz-1"]);
    });

    it("filters the cached variant list by title", async () => {
        vi.mocked(loadVisualizations).mockResolvedValue({
            data: [mockVisualization("viz-1", "ATAC peaks"), mockVisualization("viz-2", "Coverage plot")],
            totalMatches: 2,
        });

        await store.fetchVisualizations("my");

        expect(store.searchCachedVisualizations("my", "atac").map((viz) => viz.id)).toEqual(["viz-1"]);
        expect(store.searchCachedVisualizations("my", "").map((viz) => viz.id)).toEqual(["viz-1", "viz-2"]);
        expect(store.searchCachedVisualizations("my", "cov", 1)).toHaveLength(1);
        expect(store.searchCachedVisualizations("shared", "atac")).toEqual([]);
    });

    it("records a load error instead of throwing", async () => {
        vi.mocked(loadVisualizations).mockRejectedValue(new Error("boom"));

        const result = await store.fetchVisualizations("my");

        expect(result).toEqual([]);
        expect(store.loadError).toBe("boom");
        expect(store.isLoading).toBe(false);
        expect(store.hasLoadedVariant("my")).toBe(false);
    });
});

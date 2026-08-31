import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadVisualizations, type VisualizationSummary } from "@/api/visualizations";
import type { RecentPaletteItem } from "@/composables/useRecentPaletteItems";
import { useVisualizationStore } from "@/stores/visualizationStore";

import type { PaletteContext } from "../types";
import { visualizationsProvider } from "./visualizations";

vi.mock("@/api/visualizations", () => ({
    loadVisualizations: vi.fn(),
}));

const recentEntries: RecentPaletteItem[] = [];

vi.mock("@/composables/useRecentPaletteItems", () => ({
    useRecentPaletteItems: () => ({
        recentItems: (type: string) => recentEntries.filter((entry) => entry.type === type),
        addRecentItem: vi.fn(),
        clearRecentItems: vi.fn(),
    }),
}));

const VISUALIZATION_SCOPE = { key: "v", label: "Visualizations", providerId: "visualizations" };

function mockVisualization(id: string, title: string, type = "nvd3_bar"): VisualizationSummary {
    return {
        id,
        title,
        type,
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

function makeCtx(): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAdmin: false, isAnonymous: false };
}

function mockList(...visualizations: VisualizationSummary[]) {
    vi.mocked(loadVisualizations).mockResolvedValue({ data: visualizations, totalMatches: visualizations.length });
}

describe("visualizationsProvider", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.mocked(loadVisualizations).mockReset();
        recentEntries.length = 0;
    });

    it("maps a visualization to the display route the grid opens", async () => {
        mockList(mockVisualization("viz-1", "ATAC peaks"));

        const sections = (await visualizationsProvider.searchScoped?.(VISUALIZATION_SCOPE, "atac", makeCtx())) ?? [];
        const items = sections[0]?.items ?? [];

        expect(items).toHaveLength(1);
        expect(items[0]?.id).toBe("visualizations:viz-1");
        expect(items[0]?.title).toBe("ATAC peaks");
        expect(items[0]?.to).toBe("/visualizations/display?visualization=nvd3_bar&visualization_id=viz-1");
        expect(items[0]?.subtitle).toBe("nvd3_bar · Jan 2, 2026");
    });

    it("hydrates the store once and ranks the cache before merging backend hits", async () => {
        const store = useVisualizationStore();
        mockList(mockVisualization("viz-1", "ATAC peaks"), mockVisualization("viz-2", "Coverage plot"));
        await store.ensureVariantLoaded("my");
        vi.mocked(loadVisualizations).mockClear();
        // the backend repeats the cached match, which must not be listed twice
        vi.mocked(loadVisualizations).mockResolvedValueOnce({
            data: [mockVisualization("viz-2", "Coverage plot")],
            totalMatches: 1,
        });

        const sections =
            (await visualizationsProvider.searchScoped?.(VISUALIZATION_SCOPE, "coverage", makeCtx())) ?? [];

        // hydration already happened, so only the query fetch is left
        expect(loadVisualizations).toHaveBeenCalledTimes(1);
        expect(loadVisualizations).toHaveBeenCalledWith(expect.objectContaining({ search: "coverage", showOwn: true }));
        expect(sections[0]?.items.map((item) => item.id)).toEqual(["visualizations:viz-2"]);
    });

    it("queries the backend when the cache cannot answer and merges results into the store", async () => {
        vi.mocked(loadVisualizations).mockResolvedValueOnce({
            data: [mockVisualization("viz-1", "ATAC peaks")],
            totalMatches: 1,
        });
        vi.mocked(loadVisualizations).mockResolvedValueOnce({
            data: [mockVisualization("viz-9", "Genome browser")],
            totalMatches: 1,
        });

        const sections = (await visualizationsProvider.searchScoped?.(VISUALIZATION_SCOPE, "genome", makeCtx())) ?? [];

        expect(loadVisualizations).toHaveBeenCalledTimes(2);
        expect(sections[0]?.items.map((item) => item.id)).toEqual(["visualizations:viz-9"]);
        expect(useVisualizationStore().getVisualizationSummary("viz-9")?.title).toBe("Genome browser");
    });

    it("filters the cache in the unscoped fan-out and never fetches there", async () => {
        mockList(mockVisualization("viz-1", "ATAC peaks"), mockVisualization("viz-2", "Coverage plot"));
        // nothing cached yet: the fan-out contributes nothing rather than fetching
        expect(await visualizationsProvider.search("coverage", makeCtx())).toEqual([]);
        expect(loadVisualizations).not.toHaveBeenCalled();

        await useVisualizationStore().ensureVariantLoaded("my");
        vi.mocked(loadVisualizations).mockClear();

        const items = await visualizationsProvider.search("coverage", makeCtx());

        expect(items.map((item) => item.id)).toEqual(["visualizations:viz-2"]);
        expect(loadVisualizations).not.toHaveBeenCalled();
    });

    it("shows recent and latest sections for an empty scoped query", async () => {
        mockList(mockVisualization("viz-1", "ATAC peaks"), mockVisualization("viz-2", "Coverage plot"));
        recentEntries.push({ type: "visualization", id: "viz-2", name: "Coverage plot" });

        const sections = await visualizationsProvider.searchScoped?.(VISUALIZATION_SCOPE, "", makeCtx());

        expect(sections?.map((section) => section.title)).toEqual(["Recent", "Latest visualizations"]);
        expect(sections?.[0]?.items.map((item) => item.id)).toEqual(["visualizations:viz-2"]);
        expect(sections?.[1]?.items.map((item) => item.id)).toEqual(["visualizations:viz-1", "visualizations:viz-2"]);
    });

    it("keeps a recent item that is no longer cached, using its stored route", async () => {
        mockList();
        recentEntries.push({ type: "visualization", id: "viz-7", name: "Old chart", to: "/visualizations/edit?id=7" });

        const sections = await visualizationsProvider.searchScoped?.(VISUALIZATION_SCOPE, "", makeCtx());

        expect(sections?.map((section) => section.title)).toEqual(["Recent"]);
        expect(sections?.[0]?.items[0]).toMatchObject({
            id: "visualizations:viz-7",
            title: "Old chart",
            to: "/visualizations/edit?id=7",
        });
    });

    it("returns a single result section for a scoped query", async () => {
        vi.mocked(loadVisualizations).mockResolvedValueOnce({
            data: [mockVisualization("viz-1", "ATAC peaks"), mockVisualization("viz-2", "Coverage plot")],
            totalMatches: 2,
        });
        vi.mocked(loadVisualizations).mockResolvedValueOnce({
            data: [mockVisualization("viz-1", "ATAC peaks")],
            totalMatches: 1,
        });
        recentEntries.push({ type: "visualization", id: "viz-2", name: "Coverage plot" });

        const sections = await visualizationsProvider.searchScoped?.(VISUALIZATION_SCOPE, "atac", makeCtx());

        expect(sections).toHaveLength(1);
        expect(sections?.[0]?.id).toBe("results");
        expect(sections?.[0]?.items.map((item) => item.id)).toEqual(["visualizations:viz-1"]);
    });

    it("lists cached visualizations for an empty query without fetching", () => {
        const store = useVisualizationStore();
        store.saveVisualizations([mockVisualization("viz-1", "ATAC peaks")]);
        store.visualizationIdsByVariant.my = ["viz-1"];

        const items = visualizationsProvider.emptyQueryItems?.(makeCtx()) ?? [];

        expect(items.map((item) => item.id)).toEqual(["visualizations:viz-1"]);
        expect(loadVisualizations).not.toHaveBeenCalled();
    });
});

import { defineStore } from "pinia";
import { computed, ref, set } from "vue";

import { loadVisualizations, type VisualizationSummary } from "@/api/visualizations";
import { errorMessageAsString } from "@/utils/simple-error";

/** Number of visualization summaries fetched when hydrating a variant list. */
const DEFAULT_LIMIT = 25;

/** The visualization lists the palette (and other list consumers) can ask for. */
export type VisualizationVariant = "my" | "shared" | "published";

interface VariantFlags {
    showOwn: boolean;
    showShared: boolean;
    showPublished: boolean;
}

/**
 * Explicit `show_*` triplets so a variant never leaks items from another one.
 */
const VARIANT_FLAGS: Record<VisualizationVariant, VariantFlags> = {
    my: { showOwn: true, showShared: false, showPublished: false },
    shared: { showOwn: false, showShared: true, showPublished: false },
    published: { showOwn: false, showShared: false, showPublished: true },
};

const VARIANTS = Object.keys(VARIANT_FLAGS) as VisualizationVariant[];

export interface FetchVisualizationsOptions {
    /** Free text matched server-side against title, slug, tag and type. */
    search?: string;
    /** Maximum number of visualizations to request. */
    limit?: number;
}

function emptyVariantRecord<T>(value: () => T): Record<VisualizationVariant, T> {
    return Object.fromEntries(VARIANTS.map((variant) => [variant, value()])) as Record<VisualizationVariant, T>;
}

/**
 * Caches visualization *summaries* keyed by id, plus the ordered id list of each
 * variant ("my" / "shared" / "published"). Fetches merge into the same cache, so
 * a visualization visible in more than one list is stored exactly once.
 */
export const useVisualizationStore = defineStore("visualizationStore", () => {
    const storedVisualizations = ref<Record<string, VisualizationSummary>>({});
    /** Visualization ids per variant, ordered by `update_time` descending. */
    const visualizationIdsByVariant = ref(emptyVariantRecord<string[]>(() => []));
    /** Whether the unfiltered list of a variant has been fetched at least once. */
    const loadedVariants = ref(emptyVariantRecord<boolean>(() => false));
    /** Total number of visualizations matching the last unfiltered fetch. */
    const totalMatchesByVariant = ref(emptyVariantRecord<number>(() => 0));
    const isLoading = ref(false);
    const loadError = ref<string | undefined>(undefined);

    const getVisualizations = computed(() => (variant: VisualizationVariant): VisualizationSummary[] => {
        return visualizationIdsByVariant.value[variant]
            .map((id) => storedVisualizations.value[id])
            .filter((visualization): visualization is VisualizationSummary => Boolean(visualization));
    });

    const hasLoadedVariant = computed(() => (variant: VisualizationVariant) => loadedVariants.value[variant]);

    function getVisualizationSummary(id: string): VisualizationSummary | undefined {
        return storedVisualizations.value[id];
    }

    /** Merges visualization summaries into the cache, keyed (and deduped) by id. */
    function saveVisualizations(visualizations: VisualizationSummary[]) {
        for (const visualization of visualizations) {
            if (!visualization?.id) {
                continue;
            }
            set(storedVisualizations.value, visualization.id, visualization);
        }
    }

    /**
     * Fetches summaries for a variant and merges them into the cache. Unfiltered
     * fetches also (re)define the ordered id list of that variant.
     */
    async function fetchVisualizations(
        variant: VisualizationVariant,
        options: FetchVisualizationsOptions = {},
    ): Promise<VisualizationSummary[]> {
        const { search = "", limit = DEFAULT_LIMIT } = options;
        isLoading.value = true;
        loadError.value = undefined;
        try {
            const { data, totalMatches } = await loadVisualizations({
                ...VARIANT_FLAGS[variant],
                sortBy: "update_time",
                sortDesc: true,
                limit,
                search,
            });
            saveVisualizations(data);
            if (!search) {
                const ids = Array.from(new Set(data.map((visualization) => visualization.id)));
                set(visualizationIdsByVariant.value, variant, ids);
                set(totalMatchesByVariant.value, variant, totalMatches);
                set(loadedVariants.value, variant, true);
            }
            return data;
        } catch (error) {
            loadError.value = errorMessageAsString(error);
            return [];
        } finally {
            isLoading.value = false;
        }
    }

    /** Fetches a variant once; later calls resolve from the cache. */
    async function ensureVariantLoaded(
        variant: VisualizationVariant,
        limit = DEFAULT_LIMIT,
    ): Promise<VisualizationSummary[]> {
        if (!loadedVariants.value[variant]) {
            await fetchVisualizations(variant, { limit });
        }
        return getVisualizations.value(variant);
    }

    /** Client-side title filter over the cached ids of a variant. */
    function searchCachedVisualizations(
        variant: VisualizationVariant,
        query: string,
        limit = DEFAULT_LIMIT,
    ): VisualizationSummary[] {
        const term = query.trim().toLowerCase();
        const cached = getVisualizations.value(variant);
        const matches = term
            ? cached.filter((visualization) => visualization.title?.toLowerCase().includes(term))
            : cached;
        return matches.slice(0, limit);
    }

    return {
        storedVisualizations,
        visualizationIdsByVariant,
        loadedVariants,
        totalMatchesByVariant,
        isLoading,
        loadError,
        getVisualizations,
        hasLoadedVariant,
        getVisualizationSummary,
        saveVisualizations,
        fetchVisualizations,
        ensureVariantLoaded,
        searchCachedVisualizations,
    };
});

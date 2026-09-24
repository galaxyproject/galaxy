import { type Ref, ref, watch, type WatchSource } from "vue";

import { GalaxyApi } from "@/api";

import type { HistoryGraphResponse } from "./historyGraphMapper";

/**
 * Fetch the history-scoped graph from the API.
 *
 * The default call returns the full history graph (within bounds).
 * An optional (seedSrc, seedId) pair requests a focused subgraph.
 */
export function useHistoryGraphData(
    historyId: Ref<string>,
    limit: Ref<number>,
    seedSrc?: Ref<string | undefined>,
    seedId?: Ref<string | undefined>,
) {
    const graphData = ref<HistoryGraphResponse | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);

    async function fetchGraph() {
        // Only show the loading state when there's nothing to render — on
        // refetch we keep the existing graph mounted so the consumer's view
        // (pan, zoom, selection) survives until fresh data lands.
        const showLoading = graphData.value === null;
        if (showLoading) {
            loading.value = true;
        }
        error.value = null;

        try {
            const query: Record<string, unknown> = {
                limit: limit.value,
            };
            if (seedSrc?.value && seedId?.value) {
                query.seed_src = seedSrc.value;
                query.seed_id = seedId.value;
            }

            const { data, error: apiError } = await GalaxyApi().GET("/api/histories/{history_id}/graph", {
                params: {
                    path: { history_id: historyId.value },
                    query: query as any,
                },
            });

            if (apiError) {
                error.value = apiError.err_msg || "Failed to load graph";
                graphData.value = null;
            } else {
                graphData.value = data;
            }
        } catch (e) {
            error.value = e instanceof Error ? e.message : "Failed to load graph";
            graphData.value = null;
        } finally {
            if (showLoading) {
                loading.value = false;
            }
        }
    }

    const watchSources: WatchSource[] = [historyId, limit];
    if (seedSrc) {
        watchSources.push(seedSrc);
    }
    if (seedId) {
        watchSources.push(seedId);
    }
    watch(watchSources, () => fetchGraph(), { immediate: true });

    return { graphData, loading, error, refetch: fetchGraph };
}

import { type Ref, ref, watch } from "vue";

import { GalaxyApi } from "@/api";

import type { HistoryGraphResponse } from "./historyGraphMapper";

/**
 * Fetch the history-scoped graph from the API.
 *
 * The default call returns the full history graph (within bounds).
 * An optional seed parameter requests a focused subgraph.
 */
export function useHistoryGraphData(historyId: Ref<string>, limit: Ref<number>, seed?: Ref<string | undefined>) {
    const graphData = ref<HistoryGraphResponse | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);

    async function fetchGraph() {
        loading.value = true;
        error.value = null;

        try {
            const query: Record<string, unknown> = {
                limit: limit.value,
            };
            if (seed?.value) {
                query.seed = seed.value;
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
            loading.value = false;
        }
    }

    const watchSources = seed ? [historyId, limit, seed] : [historyId, limit];
    watch(watchSources, () => fetchGraph(), { immediate: true });

    return { graphData, loading, error };
}

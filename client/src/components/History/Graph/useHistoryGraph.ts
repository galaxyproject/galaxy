import { storeToRefs } from "pinia";
import { computed, type Ref, ref, watch } from "vue";

import { userOwnsHistory } from "@/api";
import { useConfig } from "@/composables/config";
import { useExtendedHistory } from "@/composables/detailedHistory";
import { addHistoryViewerSubscription, removeHistoryViewerSubscription } from "@/composables/useNotificationSSE";
import { useUserStore } from "@/stores/userStore";

import { type HistoryGraphNode, mapEdges, mapNodes, nodeKey } from "./historyGraphMapper";
import { useHistoryGraphData } from "./useHistoryGraphData";

/** Upper bound passed to the graph API's `?limit=` param. */
const FETCH_LIMIT = 500;

/**
 * Reactive history graph: initial fetch, update_time-driven refetch,
 * per-history SSE viewer subscription (Multiview pattern), and the
 * renderer-ready node / edge / focus / truncation / tool-execution projections.
 */
export function useHistoryGraph(
    historyId: Ref<string>,
    seedSrc: Ref<string | undefined>,
    seedId: Ref<string | undefined>,
) {
    const { currentUser } = storeToRefs(useUserStore());
    const { config } = useConfig();
    const { history } = useExtendedHistory(historyId.value);

    const limit = ref(FETCH_LIMIT);

    const { graphData, loading, error, refetch } = useHistoryGraphData(historyId, limit, seedSrc, seedId);

    // Refetch on update_time change. The store keeps that fresh via SSE push
    // (current/owned histories + ones we subscribe to below) or via the
    // polling fallback. Skip the initial transition since useHistoryGraphData
    // already fires `immediate: true`.
    watch(
        () => history.value?.update_time,
        (newT, oldT) => {
            if (newT && oldT && newT !== oldT) {
                refetch();
            }
        },
    );

    // In SSE mode, register a per-history viewer subscription so the server
    // pushes events for histories the current user doesn't own. Owned
    // histories already get pushes via the general channel; polling mode
    // skips this entirely.
    const needsViewerSubscription = computed(() => {
        if (!config.value?.enable_sse_updates) {
            return false;
        }
        if (!history.value || !currentUser.value) {
            return false;
        }
        return !userOwnsHistory(currentUser.value, history.value);
    });

    watch(
        [needsViewerSubscription, historyId],
        ([subscribe, id], _previous, onCleanup) => {
            if (!subscribe || !id) {
                return;
            }
            addHistoryViewerSubscription(id);
            onCleanup(() => removeHistoryViewerSubscription(id));
        },
        { immediate: true },
    );

    const focusNodeId = computed(() =>
        seedSrc.value && seedId.value ? nodeKey({ src: seedSrc.value, id: seedId.value }) : null,
    );

    // Graph structure for the renderer — GraphView measures and positions it.
    const graphNodes = computed<HistoryGraphNode[]>(() =>
        graphData.value ? mapNodes(graphData.value.nodes, graphData.value.edges) : [],
    );
    const graphEdges = computed(() => (graphData.value ? mapEdges(graphData.value.edges) : []));

    const isTruncated = computed(() => graphData.value?.truncated?.item_count_capped ?? false);

    // Backend node src is still `tool_request`; this feeds the Tool Executions tab.
    const toolExecutionNodes = computed<HistoryGraphNode[]>(() =>
        graphNodes.value.filter((node) => node.data?.src === "tool_request"),
    );

    return {
        history,
        loading,
        error,
        refetch,
        focusNodeId,
        graphNodes,
        graphEdges,
        isTruncated,
        toolExecutionNodes,
    };
}

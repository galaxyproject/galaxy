<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { GraphEdge } from "@/components/Graph/types";

import type { HistoryGraphNode } from "./historyGraphMapper";
import { historyNodeColor } from "./historyNodeColor";

import HistoryGraphNodeDetails from "./HistoryGraphNodeDetails.vue";
import GraphView from "@/components/Graph/GraphView.vue";

interface Props {
    nodes: HistoryGraphNode[];
    edges: GraphEdge[];
    focusNodeId?: string | null;
}

const props = withDefaults(defineProps<Props>(), {
    focusNodeId: null,
});

// Selected graph node — its details render in the card below the graph.
const selectedNode = ref<HistoryGraphNode | null>(null);

const nodesById = computed(() => new Map(props.nodes.map((n) => [n.id, n])));

function findProducerToolRequestNode(targetKey: string): HistoryGraphNode | null {
    // The producer of an HDCA is whichever tool_request node has an edge
    // pointing at it. Look up the source node and check its semantic type
    // — avoids any assumption about how the renderer encodes node keys.
    for (const edge of props.edges) {
        if (edge.target !== targetKey) {
            continue;
        }
        const sourceNode = nodesById.value.get(edge.source);
        if (sourceNode?.data?.src === "tool_request") {
            return sourceNode;
        }
    }
    return null;
}

function onNodeSelected(node: HistoryGraphNode | null) {
    // HDCAs are "the batch unit" — clicking one means "show the tool
    // execution that produced this collection," with all sibling jobs
    // reachable via pagination. Redirect to the producing tool_request
    // node when one is in the graph; fall through if not (NodeBody's own
    // job_source_id lookup handles single-job collections).
    if (node?.data?.src === "hdca") {
        const producer = findProducerToolRequestNode(node.id);
        if (producer) {
            selectedNode.value = producer;
            return;
        }
    }
    selectedNode.value = node;
}
</script>

<template>
    <div class="history-graph-overview">
        <div class="graph-pane rounded border" :class="{ 'with-details': !!selectedNode }">
            <GraphView
                :nodes="nodes"
                :edges="edges"
                :focus-node-id="focusNodeId"
                :node-color="historyNodeColor"
                show-scroll-overlays
                @nodeSelected="onNodeSelected" />
        </div>
        <div v-if="selectedNode" class="details-pane mt-2">
            <HistoryGraphNodeDetails :node="selectedNode" />
        </div>
        <BAlert v-else show variant="info" class="mt-2 mb-0 py-1 flex-shrink-0">
            <FontAwesomeIcon :icon="faInfoCircle" class="mr-1" />
            Click on a node in the graph above to view its details.
        </BAlert>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

// Fixed 70/30 split: graph on top, details below. `overflow: hidden` on the
// container keeps internal overflow from pushing the page, and `min-height: 0`
// on the flex items lets them honour their flex-basis instead of stretching.
.history-graph-overview {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: hidden;
}

.graph-pane {
    display: flex;
    flex: 1 1 0;
    min-height: 0;
}

// Fixed 50% only when the details pane is open; otherwise the graph absorbs
// the whole tab area.
.graph-pane.with-details {
    flex: 0 0 50%;
}

.details-pane {
    flex: 1 1 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

// Push the scroll boundary all the way down to GTabs's `.tab-content`. Each
// level in between needs `min-height: 0` so flex sizing wins over content size
// and the scroll kicks in instead of the parent overflowing.
.details-pane > :deep(*) {
    flex: 1 1 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
}

.details-pane :deep(.tabs) {
    flex: 1 1 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
}

.details-pane :deep(.tab-content) {
    flex: 1 1 0;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
}

/* Tool request nodes use the primary header colour (no dataset state). */
:deep(.node-tool-request) .graph-node-header {
    background: $brand-primary;
    color: $white;
}

/* Dataset/collection node headers use state-driven colouring via data-state. */
:deep(.node-dataset) .graph-node-header,
:deep(.node-collection) .graph-node-header {
    color: $text-color;
}
</style>

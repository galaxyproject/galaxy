<script setup lang="ts">
import type { GraphEdge } from "@/components/Graph/types";

import type { HistoryGraphNode } from "./historyGraphMapper";
import { historyNodeColor } from "./historyNodeColor";

import GraphView from "@/components/Graph/GraphView.vue";

interface Props {
    nodes: HistoryGraphNode[];
    edges: GraphEdge[];
    focusNodeId?: string | null;
}

withDefaults(defineProps<Props>(), {
    focusNodeId: null,
});

const emit = defineEmits<{ (e: "nodeSelected", node: HistoryGraphNode | null): void }>();
</script>

<template>
    <GraphView
        :nodes="nodes"
        :edges="edges"
        :focus-node-id="focusNodeId"
        :node-color="historyNodeColor"
        show-scroll-overlays
        @node-selected="emit('nodeSelected', $event)" />
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

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

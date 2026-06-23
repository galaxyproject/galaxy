<script setup lang="ts">
import { BAlert } from "bootstrap-vue";

import type { HistoryGraphNode } from "./historyGraphMapper";

import HistoryGraphNodeBody from "./HistoryGraphNodeBody.vue";

interface Props {
    /** The selected graph node, or null when nothing is selected. */
    node: HistoryGraphNode | null;
    /** Empty-state message shown when no node is selected. */
    emptyText?: string;
}

withDefaults(defineProps<Props>(), {
    emptyText: "Click on a node in the graph above to view its details.",
});
</script>

<template>
    <BAlert v-if="!node" show variant="info" class="mb-0">{{ emptyText }}</BAlert>
    <HistoryGraphNodeBody v-else :node="node" />
</template>

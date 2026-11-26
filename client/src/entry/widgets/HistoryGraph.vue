<script setup lang="ts">
import { toRef } from "vue";

import { useHistoryGraph } from "@/components/History/Graph/useHistoryGraph";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import HistoryGraphCanvas from "@/components/History/Graph/HistoryGraphCanvas.vue";
import HistoryGraphState from "@/components/History/Graph/HistoryGraphState.vue";

const props = defineProps<{
    historyId: string;
    seedSrc?: string;
    seedId?: string;
}>();

const { loading, error, focusNodeId, graphNodes, graphEdges, isTruncated, toolExecutionNodes } = useHistoryGraph(
    toRef(props, "historyId"),
    toRef(props, "seedSrc"),
    toRef(props, "seedId"),
);
</script>

<template>
    <HistoryGraphState
        :error="error"
        :loading="loading"
        :node-count="graphNodes.length"
        :execution-count="toolExecutionNodes.length">
        <GAlert v-if="isTruncated" show variant="warning" class="m-2 py-1">
            Only considering first {{ toolExecutionNodes.length }} executions.
        </GAlert>
        <HistoryGraphCanvas :nodes="graphNodes" :edges="graphEdges" :focus-node-id="focusNodeId" />
    </HistoryGraphState>
</template>

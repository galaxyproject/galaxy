<script setup lang="ts">
import { faBezierCurve, faProjectDiagram } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, ref, toRef } from "vue";

import type { EdgeStyle, GraphNode } from "@/components/Graph/types";
import { useHistoryStore } from "@/stores/historyStore";

import { useHistoryGraphData } from "./useHistoryGraphData";
import { useHistoryGraphLayout } from "./useHistoryGraphLayout";

import HistoryGraphDetails from "./HistoryGraphDetails.vue";
import HistoryGraphMinimap from "./HistoryGraphMinimap.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
import Heading from "@/components/Common/Heading.vue";
import GraphView from "@/components/Graph/GraphView.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    historyId: string;
    seedNodeId?: string;
}

const props = defineProps<Props>();

// History name
const historyStore = useHistoryStore();
const historyName = computed(() => historyStore.getHistoryNameById(props.historyId));

// Fetch params — product decisions owned here
const limit = ref(500);

const { graphData, loading, error } = useHistoryGraphData(toRef(props, "historyId"), limit, toRef(props, "seedNodeId"));

// Layout
const edgeStyle = ref<EdgeStyle>("orthogonal");
const { layout, layoutLoading } = useHistoryGraphLayout(graphData, edgeStyle);

// Selection
const selectedNode = ref<GraphNode | null>(null);

function onNodeSelected(node: GraphNode | null) {
    selectedNode.value = node;
}

const isLoading = computed(() => loading.value || layoutLoading.value);
const isTruncated = computed(() => graphData.value?.truncated?.item_count_capped ?? false);
</script>

<template>
    <div class="history-graph-view">
        <BAlert v-if="error" variant="danger" show>{{ error }}</BAlert>
        <LoadingSpan v-else-if="isLoading" message="Loading history graph" />
        <template v-else>
            <div class="ui-form-header-underlay sticky-top" />
            <div class="tool-header sticky-top bg-secondary px-2 py-1 mb-2 rounded">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="py-1 d-flex flex-gapx-1 align-items-center">
                        <FontAwesomeIcon :icon="faBezierCurve" class="fa-fw" />
                        <Heading h1 inline bold size="text">{{ historyName }}</Heading>
                    </div>
                    <GButtonGroup>
                        <GButton
                            tooltip
                            :title="'Orthogonal edges'"
                            size="small"
                            color="blue"
                            :outline="edgeStyle !== 'orthogonal'"
                            :pressed="edgeStyle === 'orthogonal'"
                            @click="edgeStyle = 'orthogonal'">
                            <FontAwesomeIcon :icon="faProjectDiagram" fixed-width />
                        </GButton>
                        <GButton
                            tooltip
                            :title="'Curved edges'"
                            size="small"
                            color="blue"
                            :outline="edgeStyle !== 'curved'"
                            :pressed="edgeStyle === 'curved'"
                            @click="edgeStyle = 'curved'">
                            <FontAwesomeIcon :icon="faBezierCurve" fixed-width />
                        </GButton>
                    </GButtonGroup>
                </div>
            </div>
            <div class="history-graph-content">
                <GraphView
                    :layout="layout"
                    :focus-node-id="seedNodeId ?? null"
                    :edge-style="edgeStyle"
                    :minimap-component="HistoryGraphMinimap"
                    @nodeSelected="onNodeSelected" />
                <HistoryGraphDetails v-if="selectedNode" :node="selectedNode" />
            </div>
            <div v-if="isTruncated" class="history-graph-truncation">
                Showing a partial graph. Not all connections are visible.
            </div>
        </template>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.history-graph-view {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 400px;
}

.history-graph-content {
    display: flex;
    flex-direction: row;
    flex: 1;
    min-height: 0;
}

.history-graph-truncation {
    padding: 0.375rem 1rem;
    background: $state-warning-bg;
    color: $state-warning-text;
    font-size: $h6-font-size;
    text-align: center;
    border-top: 1px solid $state-warning-border;
}

/* Tool request nodes use primary header (no dataset state) */
:deep(.node-tool-request) .graph-node-header {
    background: $brand-primary;
    color: $white;
}

/* Dataset/collection nodes use state-driven coloring via data-state attribute */
:deep(.node-dataset) .graph-node-header,
:deep(.node-collection) .graph-node-header {
    color: $text-color;
}
</style>

<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import type { GraphNode } from "./types";

import GraphConnector from "./GraphConnector.vue";

interface Props {
    node: GraphNode;
    selected: boolean;
    /** Dim the node when another node's lineage is in focus and this one isn't. */
    outOfFocus?: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
    (e: "select", nodeId: string): void;
    (e: "resize", nodeId: string, size: { width: number; height: number; connectorY?: number }): void;
}>();

// The node has a fixed width but content-driven height (multiline header and
// body text). A ResizeObserver reports the rendered size — and the centre Y of
// the first body row — so the graph layout can position nodes and anchor edges
// once everything is measured.
const root = ref<HTMLElement | null>(null);
let observer: ResizeObserver | null = null;
let lastEmitted = "";

function measure() {
    const el = root.value;
    if (!el) {
        return;
    }
    // The merged connectors anchor to the first body row. offsetTop is measured
    // from the node's padding edge (inside the border), so clientTop — the top
    // border width — is added to make connectorY relative to the node's outer
    // top, the origin the layout positions the node from.
    const mergedRow = el.querySelector<HTMLElement>("[data-merged-connector]");
    const connectorY = mergedRow ? el.clientTop + mergedRow.offsetTop + mergedRow.offsetHeight / 2 : undefined;
    const width = el.offsetWidth;
    const height = el.offsetHeight;
    const key = `${width}x${height}:${connectorY}`;
    if (key === lastEmitted) {
        return;
    }
    lastEmitted = key;
    emit("resize", props.node.id, { width, height, connectorY });
}

onMounted(() => {
    if (!root.value) {
        return;
    }
    // observe() fires immediately, so the initial size is reported too.
    observer = new ResizeObserver(measure);
    observer.observe(root.value);
});

onBeforeUnmount(() => observer?.disconnect());

const nodeStyle = computed(() => ({
    left: `${props.node.x}px`,
    top: `${props.node.y}px`,
    width: `${props.node.width}px`,
}));

const stateText = computed(() => (props.node.data?.stateText as string | undefined) ?? "");
const showBody = computed(() => Boolean(props.node.badge || stateText.value));
const iconSpin = computed(() => Boolean(props.node.data?.stateSpin));
</script>

<template>
    <div
        ref="root"
        class="graph-node"
        :class="[node.cssClass, { 'node-highlight': selected, 'node-out-of-focus': outOfFocus }]"
        :style="nodeStyle"
        @click.stop="emit('select', node.id)">
        <div class="graph-node-header unselectable" :data-state="node.data?.state ?? undefined">
            <FontAwesomeIcon :icon="node.icon" class="graph-node-icon" :spin="iconSpin" fixed-width />
            <span class="graph-node-label">{{ node.label }}</span>
        </div>

        <!-- Badge / state / summary body. The merged connectors anchor to the
             first body row, or to the node centre when there is no body. -->
        <div v-if="showBody" class="graph-node-body">
            <div class="graph-node-body-row" data-merged-connector>
                <span v-if="node.badge" class="badge badge-secondary">{{ node.badge }}</span>
                <span v-else class="graph-node-state">{{ stateText }}</span>
                <GraphConnector
                    v-if="node.inputConnector"
                    class="graph-node-connector graph-node-connector--input"
                    :variant="node.inputConnector" />
                <GraphConnector
                    v-if="node.outputConnector"
                    class="graph-node-connector graph-node-connector--output"
                    :variant="node.outputConnector" />
            </div>
            <div v-if="node.badge && stateText" class="graph-node-body-row">
                <span class="graph-node-state">{{ stateText }}</span>
            </div>
        </div>
        <template v-else>
            <GraphConnector
                v-if="node.inputConnector"
                class="graph-node-connector graph-node-connector--input"
                :variant="node.inputConnector" />
            <GraphConnector
                v-if="node.outputConnector"
                class="graph-node-connector graph-node-connector--output"
                :variant="node.outputConnector" />
        </template>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.graph-node {
    position: absolute;
    background: $white;
    border: solid $brand-primary 1px;
    border-radius: 0.25rem;
    cursor: pointer;
    user-select: none;
    transition:
        border-color 0.15s,
        box-shadow 0.15s,
        opacity 0.2s ease;
}

.node-out-of-focus {
    opacity: 0.35;
}

.node-highlight {
    z-index: 1001;
    border-color: $white;
    outline: 5px solid $brand-warning;
}

.graph-node-header {
    // Block flow (not flex) so the icon sits inline at the start and wrapped
    // header text uses the node's full width.
    padding: 0.25rem 0.5rem;
    font-size: $font-size-base;
    // Round the top corners to the node's inner radius (node radius minus the
    // 1px border) so the coloured header follows the outline exactly.
    border-radius: calc(0.25rem - 1px) calc(0.25rem - 1px) 0 0;
}

.graph-node-icon {
    margin-right: 0.2rem;
}

// Header and body text wrap to as many lines as needed — never truncated.
.graph-node-label {
    font-weight: 500;
    white-space: normal;
    overflow-wrap: anywhere;
}

.graph-node-body {
    border-top: solid $border-color 1px;
    font-size: $font-size-base;
}

// position: relative anchors the first row's merged connectors at its centre.
.graph-node-body-row {
    position: relative;
    padding: 0.3rem 0.75rem;
}

.graph-node-state {
    font-size: $h6-font-size;
    color: $text-muted;
    white-space: normal;
    overflow-wrap: anywhere;
}

// Connectors straddle the left/right edge of the node (or its first body row,
// whichever is the connector's positioned ancestor).
.graph-node-connector {
    position: absolute;
    top: 50%;
}

// -0.5px places the connector centre on the 1px border's centreline rather
// than on its inner edge (where left/right: 0 — the content-box edge — sits).
.graph-node-connector--input {
    left: -0.5px;
    transform: translate(-50%, -50%);
}

.graph-node-connector--output {
    right: -0.5px;
    transform: translate(50%, -50%);
}
</style>

<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { GraphNode } from "./types";

interface Props {
    node: GraphNode;
    selected: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{ (e: "select", nodeId: string): void }>();

const nodeStyle = computed(() => ({
    left: `${props.node.x}px`,
    top: `${props.node.y}px`,
    width: `${props.node.width}px`,
}));

const hasInputs = computed(() => props.node.inputs && props.node.inputs.length > 0);
const hasOutputs = computed(() => props.node.outputs && props.node.outputs.length > 0);
const hasPorts = computed(() => hasInputs.value || hasOutputs.value);
const showRule = computed(() => hasInputs.value && hasOutputs.value);
const showDataBody = computed(() => !hasPorts.value && (props.node.badge || props.node.data?.stateText));
const iconSpin = computed(() => Boolean(props.node.data?.stateSpin));
</script>

<template>
    <div
        class="graph-node card"
        :class="[node.cssClass, { 'node-highlight': selected }]"
        :style="nodeStyle"
        @click.stop="emit('select', node.id)">
        <div class="graph-node-header card-header unselectable py-1 px-2" :data-state="node.data?.state ?? undefined">
            <FontAwesomeIcon :icon="node.icon" class="graph-node-icon mr-1" :spin="iconSpin" />
            <span class="graph-node-label" :title="node.label">{{ node.label }}</span>
            <span v-if="hasPorts && node.badge" class="badge badge-light ml-auto">{{ node.badge }}</span>
        </div>
        <div v-if="showDataBody" class="card-body p-0 mx-2 my-1">
            <span v-if="node.badge" class="badge badge-secondary">{{ node.badge }}</span>
            <div v-if="node.data?.stateText" class="node-state-text">{{ node.data.stateText }}</div>
        </div>
        <div v-if="hasPorts" class="node-body card-body p-0 mx-2">
            <div v-for="input in node.inputs" :key="`in-${input.name}`" class="form-row dataRow input-data-row">
                <span class="node-port-label">{{ input.label }}</span>
            </div>
            <div v-if="showRule" class="rule" />
            <div v-for="output in node.outputs" :key="`out-${output.name}`" class="form-row dataRow output-data-row">
                <span class="node-port-label">{{ output.label }}</span>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.graph-node {
    position: absolute;
    cursor: pointer;
    user-select: none;
    border: solid $brand-primary 1px;
    transition:
        border-color 0.15s,
        box-shadow 0.15s,
        opacity 0.2s ease;
}

.node-highlight {
    z-index: 1001;
    border: solid $white 1px;
    box-shadow: 0 0 0 3px $brand-primary;
}

.graph-node-header {
    font-size: $font-size-base;
}

.graph-node-label {
    font-weight: 500;
    word-break: break-word;
}

.node-body {
    font-size: $h6-font-size;
}

.node-state-text {
    font-size: $h6-font-size;
    color: $text-muted;
    padding: 2px 0;
}

.form-row {
    padding: 1px 0;
}

.output-data-row {
    text-align: right;
}

.node-port-label {
    color: $text-color;
    padding: 0 2px;
}

.rule {
    height: 0;
    border: none;
    border-bottom: dotted $brand-primary 1px;
    margin: 0;
}
</style>

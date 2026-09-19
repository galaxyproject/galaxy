<script setup lang="ts">
import { computed } from "vue";

import { getZoomInLevel, getZoomOutLevel, isMaxZoom, isMinZoom } from "@/utils/zoomLevels";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

const props = defineProps({
    zoomLevel: { type: Number, default: 1 },
});

const emit = defineEmits<{
    (e: "onZoom", zoom: number): void;
}>();

const zoomDefault = 1;
const zoomPercentage = computed(() => Math.round(props.zoomLevel * 100));

function onZoomIn() {
    emit("onZoom", getZoomInLevel(props.zoomLevel));
}

function onZoomOut() {
    emit("onZoom", getZoomOutLevel(props.zoomLevel));
}

function onZoomReset() {
    emit("onZoom", zoomDefault);
}
</script>

<template>
    <GButtonGroup class="zoom-control float-right">
        <GButton
            :disabled="isMinZoom(props.zoomLevel)"
            class="fa fa-minus"
            title="Zoom Out"
            size="small"
            icon-only
            aria-label="Zoom Out"
            @click="onZoomOut" />
        <GButton
            tooltip
            class="zoom-reset"
            transparent
            title="Reset Zoom Level"
            size="small"
            aria-label="Reset Zoom Level"
            @click="onZoomReset">
            {{ zoomPercentage }}%
        </GButton>
        <GButton
            :disabled="isMaxZoom(props.zoomLevel)"
            class="fa fa-plus"
            title="Zoom In"
            size="small"
            icon-only
            aria-label="Zoom In"
            @click="onZoomIn" />
    </GButtonGroup>
</template>

<style scoped>
.zoom-reset {
    width: 4rem;
}
.zoom-control {
    position: absolute;
    left: 1rem;
    bottom: 1rem;
    cursor: pointer;
    z-index: 2000;
}
</style>

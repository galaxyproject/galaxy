<script setup lang="ts">
import { faMinus, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { getZoomInLevel, getZoomOutLevel, isMaxZoom, isMinZoom } from "@/utils/zoomLevels";

import GButton from "@/components/BaseComponents/GButton.vue";

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
    <div class="zoom-control float-right">
        <GButton
            :disabled="isMinZoom(props.zoomLevel)"
            title="Zoom Out"
            size="small"
            outline
            icon-only
            aria-label="Zoom Out"
            @click="onZoomOut">
            <FontAwesomeIcon :icon="faMinus" fixed-width />
        </GButton>
        <GButton
            tooltip
            class="zoom-reset"
            outline
            title="Reset Zoom Level"
            pill
            size="small"
            aria-label="Reset Zoom Level"
            @click="onZoomReset">
            {{ zoomPercentage }}%
        </GButton>
        <GButton
            :disabled="isMaxZoom(props.zoomLevel)"
            title="Zoom In"
            size="small"
            outline
            icon-only
            aria-label="Zoom In"
            @click="onZoomIn">
            <FontAwesomeIcon :icon="faPlus" fixed-width />
        </GButton>
    </div>
</template>

<style scoped>
.zoom-reset {
    display: block;
    width: 4rem;
}
.zoom-control {
    position: absolute;
    left: 1rem;
    bottom: 1rem;
    cursor: pointer;
    z-index: 2000;
    display: flex;
    flex-direction: row;
    gap: 0.5rem;
}
</style>

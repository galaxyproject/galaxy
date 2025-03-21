<script setup lang="ts">
import BootstrapVue from "bootstrap-vue";
import Vue, { computed } from "vue";

import { getZoomInLevel, getZoomOutLevel, isMaxZoom, isMinZoom } from "./modules/zoomLevels";

Vue.use(BootstrapVue);

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
    <span class="zoom-control float-right btn-group-horizontal">
        <b-button
            :disabled="isMinZoom(props.zoomLevel)"
            role="button"
            class="fa fa-minus"
            title="缩小"
            size="sm"
            aria-label="缩小"
            @click="onZoomOut" />
        <b-button
            v-b-tooltip.hover
            role="button"
            class="zoom-reset"
            variant="light"
            title="重置缩放级别"
            size="sm"
            aria-label="重置缩放级别"
            @click="onZoomReset">
            {{ zoomPercentage }}%
        </b-button>
        <b-button
            :disabled="isMaxZoom(props.zoomLevel)"
            role="button"
            class="fa fa-plus"
            title="放大"
            size="sm"
            aria-label="放大"
            @click="onZoomIn" />
    </span>
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

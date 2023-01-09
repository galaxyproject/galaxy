<template>
    <span class="zoom-control float-right btn-group-horizontal">
        <b-button
            v-b-tooltip.hover
            :disabled="isMin"
            role="button"
            class="fa fa-minus"
            title="Zoom Out"
            size="sm"
            aria-label="Zoom Out"
            @click="onZoomOut" />
        <b-button
            v-b-tooltip.hover
            role="button"
            class="zoom-reset"
            variant="light"
            title="Reset Zoom Level"
            size="sm"
            aria-label="Reset Zoom Level"
            @click="onZoomReset">
            {{ zoomPercentage }}%
        </b-button>
        <b-button
            v-b-tooltip.hover
            :disabled="isMax"
            role="button"
            class="fa fa-plus"
            title="Zoom In"
            size="sm"
            aria-label="Zoom In"
            @click="onZoomIn" />
    </span>
</template>

<script lang="ts" setup>
import Vue, { computed } from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

const props = withDefaults(
    defineProps<{
        zoomLevel: number;
    }>(),
    {
        zoomLevel: 1,
    }
);
const emit = defineEmits(["onZoom"]);

const zoomDefault = 1;
const zoomLevels = [0.1, 0.2, 0.25, 0.33, 0.5, 0.67, 0.75, 0.8, 0.9, 1, 1.1, 1.25, 1.33, 1.5, 2, 2.5, 3, 4, 5];
const isMin = computed(() => Math.round(props.zoomLevel * 100) == Math.round(zoomLevels[0] * 100));
const isMax = computed(() => Math.round(props.zoomLevel * 100) == Math.round(zoomLevels.at(-1)! * 100));
const zoomPercentage = computed(() => Math.round(props.zoomLevel * 100));
const index = computed(() => {
    let index = zoomLevels.indexOf(props.zoomLevel);
    if (index < 0) {
        const closest = zoomLevels.reduce((prev, curr) => {
            return Math.abs(curr - props.zoomLevel) < Math.abs(prev - props.zoomLevel) ? curr : prev;
        });
        index = zoomLevels.indexOf(closest);
    }
    return index;
});
function onZoomIn() {
    const zoomLevel = zoomLevels[index.value + 1];
    if (zoomLevel) {
        emit("onZoom", zoomLevel);
    }
}
function onZoomOut() {
    const zoomLevel = zoomLevels[index.value - 1];
    if (zoomLevel) {
        emit("onZoom", zoomLevel);
    }
}
function onZoomReset() {
    emit("onZoom", zoomDefault);
}
</script>

<style scoped>
.zoom-reset {
    width: 4rem;
}
.zoom-control {
    position: absolute;
    left: 1rem;
    bottom: 1rem;
    cursor: pointer;
    z-index: 1002;
}
</style>

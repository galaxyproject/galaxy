<template>
    <span class="zoom-control float-right btn-group-horizontal">
        <b-button
            v-b-tooltip.hover
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
            role="button"
            class="fa fa-plus"
            title="Zoom In"
            size="sm"
            aria-label="Zoom In"
            @click="onZoomIn" />
    </span>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        zoomLevel: {
            type: Number,
            default: 1,
        },
    },
    data() {
        return {
            zoomLevels: [
                0.1, 0.2, 0.25, 0.33, 0.5, 0.67, 0.75, 0.8, 0.9, 1, 1.1, 1.25, 1.33, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9,
                10,
            ],
            zoomDefault: 1,
        };
    },
    computed: {
        zoomPercentage() {
            return Math.floor(this.zoomLevel * 100);
        },
        index() {
            let index = this.zoomLevels.indexOf(this.zoomLevel);
            if (index < 0) {
                const closest = this.zoomLevels.reduce((prev, curr) => {
                    return Math.abs(curr - this.zoomLevel) < Math.abs(prev - this.zoomLevel) ? curr : prev;
                });
                index = this.zoomLevels.indexOf(closest);
            }
            return index;
        },
    },
    methods: {
        onZoomIn() {
            const zoomLevel = this.zoomLevels[this.index + 1];
            if (zoomLevel) {
                this.$emit("onZoom", zoomLevel);
            }
        },
        onZoomOut() {
            const zoomLevel = this.zoomLevels[this.index - 1];
            if (zoomLevel) {
                this.$emit("onZoom", zoomLevel);
            }
        },
        onZoomReset() {
            this.$emit("onZoom", this.zoomDefault);
        },
    },
};
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

<script setup>
import { zoom, zoomIdentity } from "d3-zoom";
import { ref, onMounted } from "vue";
import { pointer, select } from "d3-selection";

const props = defineProps({
    zoom: {
        type: Number,
        default: 1,
    },
    minZoom: {
        type: Number,
        default: 0.2,
    },
    maxZoom: {
        type: Number,
        default: 5,
    },
});

const emit = defineEmits(["transform"]);

const viewport = ref(null);
const transform = { x: 0, y: 0, zoom: props.zoom };
let isZoomingOrPanning = false;
const panOnScrollSpeed = 0.5;

const eventToTransform = (transform) => {
    return `translate(${transform.x}px, ${transform.y}px) scale(${transform.k})`;
};

onMounted(() => {
    const d3Zoom = zoom().scaleExtent([props.minZoom, props.maxZoom]);
    const d3Selection = select(viewport.value).call(d3Zoom);
    const d3ZoomHandler = d3Selection.on("wheel.zoom");
    const updatedTransform = zoomIdentity.translate(transform.x, transform.y).scale(transform.zoom);
    d3Zoom.transform(d3Selection, updatedTransform);

    d3Selection
        .on("wheel", (event) => {
            event.preventDefault();
            event.stopImmediatePropagation();

            const currentZoom = d3Selection.property("__zoom").k || 1;

            // if (event.ctrlKey && zoomOnPinch) {
            //   // taken from https://github.com/d3/d3-zoom/blob/master/src/zoom.js
            const pinchDelta = -event.deltaY * (event.deltaMode === 1 ? 0.05 : event.deltaMode ? 1 : 0.002) * 10;
            const point = pointer(event);
            const zoom = currentZoom * 2 ** pinchDelta;
            d3Zoom.scaleTo(d3Selection, zoom, point);

            //   return
            // }

            // increase scroll speed in firefox
            // firefox: deltaMode === 1; chrome: deltaMode === 0
            // const deltaNormalize = event.deltaMode === 1 ? 20 : 1;
            // const deltaX = event.deltaX * deltaNormalize;
            // const deltaY = event.deltaY * deltaNormalize;

            // d3Zoom.translateBy(
            //     d3Selection,
            //     -(deltaX / currentZoom) * panOnScrollSpeed,
            //     -(deltaY / currentZoom) * panOnScrollSpeed
            // );
        })
        .on("wheel.zoom", null);

    d3Zoom.on("start", (event) => {
        isZoomingOrPanning = true;
        emit("transform", event.transform);
    });

    d3Zoom.on("end", (event) => {
        isZoomingOrPanning = false;
        emit("transform", event.transform);
    });
});
</script>
<template>
    <div ref="viewport">
        <slot></slot>
    </div>
</template>

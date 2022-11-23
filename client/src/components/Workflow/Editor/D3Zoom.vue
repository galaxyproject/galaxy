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

// if element is draggable it may implement its own drag handler,
// but d3zoom would call preventDefault
const filter = (event) => {
    const isDraggable = event.srcElement.draggable;
    console.log(event);
    return !isDraggable;
};

const d3Zoom = zoom().filter(filter).scaleExtent([props.minZoom, props.maxZoom]);

function setZoom(zoom) {
    const d3Selection = select(viewport.value).call(d3Zoom);
    d3Zoom.scaleTo(d3Selection, zoom);
}

function panBy(panBy) {
    const d3Selection = select(viewport.value).call(d3Zoom);
    d3Zoom.translateBy(d3Selection, panBy.x, panBy.y);
}

function moveTo(coordinate) {
    const d3Selection = select(viewport.value).call(d3Zoom);
    d3Zoom.translateTo(d3Selection, coordinate.x, coordinate.y);
}

defineExpose({ setZoom, panBy, moveTo });

onMounted(() => {
    const d3Selection = select(viewport.value).call(d3Zoom);
    const updatedTransform = zoomIdentity.translate(transform.x, transform.y).scale(transform.zoom);
    d3Zoom.transform(d3Selection, updatedTransform);

    d3Selection
        .on("wheel", (event) => {
            event.preventDefault();
            event.stopImmediatePropagation();

            const currentZoom = d3Selection.property("__zoom").k || 1;

            const pinchDelta = -event.deltaY * (event.deltaMode === 1 ? 0.05 : event.deltaMode ? 1 : 0.002) * 10;
            const point = pointer(event);
            const zoom = currentZoom * 2 ** pinchDelta;
            d3Zoom.scaleTo(d3Selection, zoom, point);
        })
        .on("wheel.zoom", null);

    d3Zoom.on("zoom", (event) => {
        emit("transform", event.transform);
    });

    d3Zoom.on("start", (event) => {
        emit("transform", event.transform);
    });

    d3Zoom.on("end", (event) => {
        emit("transform", event.transform);
    });
});
</script>
<template>
    <div ref="viewport">
        <slot></slot>
    </div>
</template>

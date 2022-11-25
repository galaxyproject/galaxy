<script setup>
import { ref, inject, reactive } from "vue";
import { useElementSize } from "@vueuse/core";
import { useDraggable } from "./composables/useDraggable.js";

const props = defineProps({
    rootOffset: {
        type: Object,
        required: true,
    },
    preventDefault: {
        type: Boolean,
        default: true,
    },
    stopPropagation: {
        type: Boolean,
        default: true,
    },
});

const emit = defineEmits(["mousedown", "mouseup", "move", "dragstart"]);

const draggable = ref();
const size = reactive(useElementSize(draggable));
const transform = inject("transform");

const onStart = (position, event) => {
    emit("start");
    emit("mousedown", event);
    if (event.type == "dragstart") {
        // I guess better than copy ?
        event.dataTransfer.effectAllowed = "link";
        emit("dragstart", event);
    }
};

const onMove = (position, event) => {
    if (event.type == "drag" && event.x == 0 && event.y == 0) {
        // the last drag event has no coordinate ... this is obviously a hack!
        return;
    }
    position.unscaled = { ...position, ...size };
    position.x = (position.x - props.rootOffset.x - transform.x) / transform.k;
    position.y = (position.y - props.rootOffset.y - transform.y) / transform.k;
    emit("move", position, event);
};

const onEnd = (position, event) => {
    emit("stop");
    emit("mouseup");
};

useDraggable(draggable, {
    preventDefault: props.preventDefault,
    stopPropagation: props.stopPropagation,
    useCapture: false,
    onStart: onStart,
    onMove: onMove,
    onEnd: onEnd,
});
</script>
<template>
    <div ref="draggable">
        <slot></slot>
    </div>
</template>

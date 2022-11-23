<script setup>
import { ref, inject, reactive } from "vue";
import { useDraggable, useElementSize } from "@vueuse/core";

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

const emit = defineEmits(["mousedown", "mouseup", "move"]);

const draggable = ref();
const size = reactive(useElementSize(draggable));
const transform = inject("transform");

const onStart = (position, event) => {
    emit("start");
    emit("mousedown", event);
};

const onMove = (position, event) => {
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

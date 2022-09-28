<script setup>
import { ref, inject } from "vue";
import { useDraggable } from "@vueuse/core";

const props = defineProps({
    rootOffset: {
        type: Object,
        required: false,
    },
});

const emit = defineEmits(["mousedown", "mouseup", "move"]);

const draggable = ref();
const transform = inject("transform");

const onStart = (position, event) => {
    emit("mousedown", event);
};

const onMove = (position, event) => {
    position.x = (position.x - props.rootOffset.x - transform.x) / transform.k;
    position.y = (position.y - props.rootOffset.y - transform.y) / transform.k;
    emit("move", position);
};

const onEnd = (position, event) => {
    emit("mouseup");
};

useDraggable(draggable, {
    preventDefault: true,
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

<script lang="ts" setup>
import { ref, inject, reactive } from "vue";
import type { Ref } from "vue";
import { useElementSize } from "@vueuse/core";
import { useDraggable } from "./composables/useDraggable.js";
import type { ZoomTransform } from "d3-zoom";

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
    dragData: {
        type: Object,
        required: false,
        default: null,
    },
});

const emit = defineEmits(["mousedown", "mouseup", "move", "dragstart", "start", "stop"]);

const draggable = ref();
const size = reactive(useElementSize(draggable));
const transform: Ref<ZoomTransform> | undefined = inject("transform");

const onStart = (position: any, event: DragEvent) => {
    emit("start");
    emit("mousedown", event);
    if (event.type == "dragstart") {
        // I guess better than copy ?
        event.dataTransfer!.effectAllowed = "link";
        if (props.dragData) {
            event.dataTransfer!.setData("text/plain", JSON.stringify(props.dragData));
        }
        emit("dragstart", event);
    }
};

const onMove = (position: any, event: DragEvent) => {
    if (event.type == "drag" && event.x == 0 && event.y == 0) {
        // the last drag event has no coordinate ... this is obviously a hack!
        return;
    }
    const newPosition = {
        unscaled: { ...position, ...size },
        x: (position.x - props.rootOffset.x - transform!.value.x) / transform!.value.k,
        y: (position.y - props.rootOffset.y - transform!.value.y) / transform!.value.k,
    };
    emit("move", newPosition, event);
};

const onEnd = (position: any, event: DragEvent) => {
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

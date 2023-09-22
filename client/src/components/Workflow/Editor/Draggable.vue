<script setup lang="ts">
import { ref, inject, reactive, PropType } from "vue";
import type { Ref } from "vue";
import { useAnimationFrameSize } from "@/composables/sensors/animationFrameSize";
import { useAnimationFrameThrottle } from "@/composables/throttle";
import { useDraggable } from "./composables/useDraggable.js";
import type { ZoomTransform } from "d3-zoom";

const props = defineProps({
    rootOffset: {
        type: Object as PropType<Position>,
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

let dragImg: HTMLImageElement | undefined;
const draggable = ref();
const size = reactive(useAnimationFrameSize(draggable));
const transform: Ref<ZoomTransform> | undefined = inject("transform");

type Position = { x: number; y: number };

const { throttle } = useAnimationFrameThrottle();

let dragging = false;

const onStart = (position: Position, event: DragEvent) => {
    emit("start");
    emit("mousedown", event);

    if (event.type == "dragstart") {
        dragImg = document.createElement("img");
        dragImg.src = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
        document.body.appendChild(dragImg);
        // I guess better than copy ?
        event.dataTransfer!.effectAllowed = "link";
        try {
            event.dataTransfer!.setDragImage(dragImg, 0, 0);
        } catch (e) {
            console.error(e);
        }
        if (props.dragData) {
            event.dataTransfer!.setData("text/plain", JSON.stringify(props.dragData));
        }
        emit("dragstart", event);
    }
};

const onMove = (position: Position, event: DragEvent) => {
    dragging = true;

    if (event.type == "drag" && event.x == 0 && event.y == 0) {
        // the last drag event has no coordinate ... this is obviously a hack!
        return;
    }

    throttle(() => {
        if (dragging) {
            const newPosition = {
                unscaled: { ...position, ...size },
                x: (position.x - props.rootOffset.x - transform!.value.x) / transform!.value.k,
                y: (position.y - props.rootOffset.y - transform!.value.y) / transform!.value.k,
            };
            emit("move", newPosition, event);
        }
    });
};

const onEnd = (position: Position, event: DragEvent) => {
    if (dragImg) {
        document.body.removeChild(dragImg);
    }

    dragging = false;
    emit("mouseup");
    emit("stop");
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

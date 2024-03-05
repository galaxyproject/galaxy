<script setup lang="ts">
import type { ZoomTransform } from "d3-zoom";
import { storeToRefs } from "pinia";
import type { Ref } from "vue";
import { computed, inject, PropType, reactive, ref } from "vue";

import { useAnimationFrameSize } from "@/composables/sensors/animationFrameSize";
import { useAnimationFrameThrottle } from "@/composables/throttle";
import { useWorkflowStores } from "@/composables/workflowStores";

import { useMultidrag } from "./composables/multidrag";
import { useMultiSelect } from "./composables/multiSelect";
import { useDraggable } from "./composables/useDraggable";

const props = defineProps({
    rootOffset: {
        type: Object as PropType<Position>,
        required: true,
    },
    position: {
        type: Object as PropType<Position | null>,
        default: null,
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
    disabled: {
        type: Boolean,
        default: false,
    },
    snappable: {
        type: Boolean,
        default: true,
    },
});

const emit = defineEmits<{
    (e: "mousedown", event: DragEvent): void;
    (e: "mouseup", event: DragEvent): void;
    (e: "move", position: Position & { unscaled: Position & Size }, event: DragEvent): void;
    (e: "dragstart", event: DragEvent): void;
    (e: "start"): void;
    (e: "stop"): void;
}>();

let dragImg: HTMLImageElement | null = null;
const draggable = ref();
const size = reactive(useAnimationFrameSize(draggable));
const transform: Ref<ZoomTransform> | undefined = inject("transform");

type Position = { x: number; y: number };
type Size = { width: number; height: number };

const { throttle } = useAnimationFrameThrottle();

let dragging = false;

const { multidragStart, multidragEnd, multidragMove } = useMultidrag();
const { anySelected, multiSelectedSteps, multiSelectedComments } = useMultiSelect();

const onStart = (_position: Position, event: DragEvent) => {
    emit("start");
    emit("mousedown", event);

    if (anySelected.value && props.position) {
        multidragStart(props.position, multiSelectedSteps.value, multiSelectedComments.value);
    }

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

const { toolbarStore } = useWorkflowStores();
const { snapActive } = storeToRefs(toolbarStore);

function getSnappedPosition<T extends Position>(position: T) {
    if (props.snappable && snapActive.value) {
        return {
            ...position,
            x: Math.round(position.x / toolbarStore.snapDistance) * toolbarStore.snapDistance,
            y: Math.round(position.y / toolbarStore.snapDistance) * toolbarStore.snapDistance,
        } as T;
    } else {
        return {
            ...position,
            x: position.x,
            y: position.y,
        } as T;
    }
}

let previousPosition: Position | undefined;

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

            const snapped = getSnappedPosition(newPosition);

            if (!previousPosition || previousPosition.x !== snapped.x || previousPosition.y !== snapped.y) {
                emit("move", snapped, event);
            }

            multidragMove(snapped);
            previousPosition = snapped;
        }
    });
};

const onEnd = (_position: Position, event: DragEvent) => {
    if (dragImg) {
        document.body.removeChild(dragImg);
        dragImg = null;
    }

    dragging = false;
    multidragEnd();

    emit("mouseup", event);
    emit("stop");
};

const maybeDraggable = computed(() => (props.disabled ? null : draggable.value));

useDraggable(maybeDraggable, {
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

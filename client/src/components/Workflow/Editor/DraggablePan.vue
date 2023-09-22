<script setup lang="ts">
import type { PropType, UnwrapRef } from "vue";
import Draggable from "./Draggable.vue";
import type { UseElementBoundingReturn } from "@vueuse/core";

const props = defineProps({
    rootOffset: {
        type: Object as PropType<UnwrapRef<UseElementBoundingReturn>>,
        required: true,
    },
    scale: {
        type: Number,
        required: false,
        default: 1,
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

type Size = { width: number; height: number };
type Position = { x: number; y: number };

type MovePosition = Position & {
    unscaled: Position & Size;
};

const emit = defineEmits<{
    (e: "pan-by", position: Position): void;
    (e: "move", position: MovePosition, event?: MouseEvent): void;
    (e: "mouseup", event: MouseEvent): void;
}>();

let isPanning = false;
const panBy: Position = { x: 0, y: 0 };
let movePosition: MovePosition = {
    x: 0,
    y: 0,
    unscaled: {
        x: 0,
        y: 0,
        width: 0,
        height: 0,
    },
};

let previousTimestamp: number | undefined;

function pan(timestamp: number) {
    if (isPanning) {
        if (!previousTimestamp) {
            previousTimestamp = timestamp;
        }

        const deltaTime = (timestamp - previousTimestamp) / 1000;
        const scaledPan = { x: panBy.x * deltaTime, y: panBy.y * deltaTime };

        emit("pan-by", scaledPan);

        // we need to move in the opposite direction of the pan
        movePosition.x -= scaledPan.x;
        movePosition.y -= scaledPan.y;

        emit("move", movePosition);

        previousTimestamp = timestamp;
        requestAnimationFrame(pan);
    } else {
        previousTimestamp = undefined;
    }
}

const panSpeedFactor = 6;

function onMove(position: MovePosition, event: MouseEvent) {
    let doPan = false;

    panBy.x = 0;
    panBy.y = 0;

    const deltaSpeed = (delta: number) => {
        const scaledDelta = Math.abs((delta * panSpeedFactor) / props.scale);
        const clampedDelta = Math.min(scaledDelta, 1200 / props.scale);
        return clampedDelta;
    };

    const unscaled = position.unscaled;

    const deltaLeft = unscaled.x - props.rootOffset.left;
    const deltaRight = props.rootOffset.right - unscaled.x - unscaled.width * props.scale;

    const deltaTop = unscaled.y - props.rootOffset.top;
    const deltaBottom = props.rootOffset.bottom - unscaled.y - unscaled.height * props.scale;

    if (deltaLeft < 0) {
        panBy.x = deltaSpeed(deltaLeft);
        doPan = true;
    }

    if (deltaTop < 0) {
        panBy.y = deltaSpeed(deltaTop);
        doPan = true;
    }

    if (deltaRight < 0) {
        panBy.x = -deltaSpeed(deltaRight);
        doPan = true;
    }

    if (deltaBottom < 0) {
        panBy.y = -deltaSpeed(deltaBottom);
        doPan = true;
    }

    movePosition = { ...position };

    if (!doPan) {
        emit("move", position, event);
        isPanning = false;
    }

    if (doPan && !isPanning) {
        isPanning = true;
        requestAnimationFrame(pan);
    }
}

function onMouseUp(e: MouseEvent) {
    isPanning = false;
    emit("mouseup", e);
}
</script>

<template>
    <Draggable
        :root-offset="rootOffset"
        :prevent-default="preventDefault"
        :stop-propagation="stopPropagation"
        :drag-data="dragData"
        @move="onMove"
        @mouseup="onMouseUp"
        v-on="$listeners">
        <slot></slot>
    </Draggable>
</template>

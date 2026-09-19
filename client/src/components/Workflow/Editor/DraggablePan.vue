<script setup lang="ts">
import type { UseElementBoundingReturn } from "@vueuse/core";
import type { PropType, UnwrapRef } from "vue";

import Draggable from "./Draggable.vue";

const props = defineProps({
    rootOffset: {
        type: Object as PropType<UnwrapRef<UseElementBoundingReturn>>,
        required: true,
    },
    position: {
        type: Object as PropType<Position>,
        default: null,
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
    disabled: {
        type: Boolean,
        default: false,
    },
    panMargin: {
        type: Number,
        default: 60,
    },
    snappable: {
        type: Boolean,
        default: true,
    },
    selected: {
        type: Boolean,
        default: false,
    },
});

type Position = { x: number; y: number };

type MovePosition = Position & {
    unscaled: Position;
};

const emit = defineEmits<{
    (e: "pan-by", position: Position): void;
    (e: "move", position: MovePosition, event?: MouseEvent): void;
    (e: "mouseup", event: MouseEvent): void;
    (e: "mousedown", event: MouseEvent): void;
    (e: "start"): void;
}>();

let isPanning = false;
const panBy: Position = { x: 0, y: 0 };
let movePosition: MovePosition = {
    x: 0,
    y: 0,
    unscaled: {
        x: 0,
        y: 0,
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

    const deltaLeft = event.pageX - props.rootOffset.left - props.panMargin;
    const deltaRight = props.rootOffset.right - event.pageX - props.panMargin;

    const deltaTop = event.pageY - props.rootOffset.top - props.panMargin;
    const deltaBottom = props.rootOffset.bottom - event.pageY - props.panMargin;

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

function onStart() {
    emit("start");
}
</script>

<template>
    <Draggable
        :root-offset="rootOffset"
        :position="props.position"
        :prevent-default="preventDefault"
        :stop-propagation="stopPropagation"
        :drag-data="dragData"
        :disabled="disabled"
        :snappable="snappable"
        :selected="selected"
        @move="onMove"
        @mouseup="onMouseUp"
        @start="onStart"
        @mousedown="(e) => emit('mousedown', e)"
        v-on="$listeners">
        <slot></slot>
    </Draggable>
</template>

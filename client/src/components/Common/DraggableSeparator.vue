<script setup lang="ts">
import { useDebounce, useDraggable, useElementBounding } from "@vueuse/core";
import { computed, onMounted, ref, watch } from "vue";

import { useEmit } from "@/composables/eventEmitter";
import { useClamp } from "@/composables/math";
import { useAnimationFrameThrottle } from "@/composables/throttle";

const props = withDefaults(
    defineProps<{
        position: number;
        min?: number;
        max?: number;
        showDelay?: number;
        keyboardStepSize?: number;
        side: "left" | "right";
    }>(),
    {
        showDelay: 100,
        keyboardStepSize: 50,
        min: 0,
        max: Infinity,
    }
);

const emit = defineEmits<{
    (e: "positionChanged", position: number): void;
    (e: "visibilityChanged", isVisible: boolean): void;
    (e: "dragging", isDragging: boolean): void;
}>();

const { throttle } = useAnimationFrameThrottle();

const draggable = ref<HTMLButtonElement | null>(null);
const positionedParent = ref<HTMLElement | null>(null);

onMounted(() => {
    positionedParent.value = (draggable.value?.offsetParent as HTMLElement) ?? null;
});

const rootBoundingBox = useElementBounding(positionedParent);

const { position: draggablePosition, isDragging } = useDraggable(draggable, {
    preventDefault: true,
    exact: true,
    initialValue: { x: props.position, y: 0 },
});

useEmit(isDragging, emit, "dragging");

const handlePosition = useClamp(
    ref(props.position),
    () => props.min,
    () => props.max
);

useEmit(handlePosition, emit, "positionChanged");

watch(
    () => props.position,
    () => (handlePosition.value = props.position)
);

const borderWidth = 6;

function updatePosition() {
    if (props.side === "left") {
        handlePosition.value = draggablePosition.value.x - rootBoundingBox.left.value + borderWidth;
    } else {
        const clientWidth = document.body.clientWidth;
        const rootRightDistance = document.body.clientWidth - rootBoundingBox.right.value;
        handlePosition.value = clientWidth - draggablePosition.value.x - rootRightDistance - borderWidth;
    }
}

watch(
    () => draggablePosition.value,
    () => throttle(updatePosition)
);

const hoverDraggable = ref(false);

const hoverDraggableDebounced = useDebounce(
    hoverDraggable,
    computed(() => props.showDelay)
);

const showHover = computed(() => (hoverDraggable.value && hoverDraggableDebounced.value) || isDragging.value);

useEmit(showHover, emit, "visibilityChanged");

function onKeyLeft() {
    handlePosition.value -= props.keyboardStepSize;
}

function onKeyRight() {
    handlePosition.value += props.keyboardStepSize;
}

const style = computed(() => ({
    "--position": handlePosition.value + "px",
}));
</script>

<template>
    <button
        ref="draggable"
        class="drag-handle"
        :class="[`side-${props.side}`, { show: showHover }]"
        :style="style"
        @mouseenter="hoverDraggable = true"
        @focusin="hoverDraggable = true"
        @mouseout="hoverDraggable = false"
        @focusout="hoverDraggable = false"
        @keydown.left="onKeyLeft"
        @keydown.right="onKeyRight">
        <span class="sr-only"> Resizable drag handle </span>
    </button>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

$border-width: 6px;

.drag-handle {
    --position: 0;

    background-color: transparent;
    border: none;
    border-radius: 0;
    position: absolute;
    width: $border-width;
    padding: 0;
    height: 100%;
    z-index: 10000;

    --hover-expand: 4px;

    &:hover {
        cursor: ew-resize;
        width: calc($border-width + var(--hover-expand));
    }

    &.side-left {
        left: var(--position);
        margin-left: -$border-width;
    }

    &.side-right {
        right: var(--position);
        margin-right: -$border-width;
    }

    &::after {
        display: block;
        content: "";
        position: absolute;
        top: 0;
        width: $border-width;
        height: 100%;
        background-color: transparent;
        transition: background-color 0.1s;
    }

    &.show::after {
        background-color: $brand-info;
    }

    &.side-left.show::after {
        left: 0;
    }

    &.side-right.show::after {
        right: 0;
    }
}
</style>

<script setup lang="ts">
import { useDebounce, useDraggable } from "@vueuse/core";
import { computed, ref, watch } from "vue";

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
        additionalOffset?: number;
    }>(),
    {
        showDelay: 100,
        keyboardStepSize: 50,
        min: -Infinity,
        max: Infinity,
        additionalOffset: 0,
    }
);

const emit = defineEmits<{
    (e: "positionChanged", position: number): void;
    (e: "visibilityChanged", isVisible: boolean): void;
    (e: "dragging", isDragging: boolean): void;
}>();

const { throttle } = useAnimationFrameThrottle();

const draggable = ref<HTMLButtonElement | null>(null);

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

function updatePosition() {
    handlePosition.value = draggablePosition.value.x;
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
        :class="`side-${props.side}`"
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
$border-width: 8px;

.drag-handle {
    --position: 0;

    background-color: transparent;
    background: none;
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
    }

    &.side-right {
        right: var(--position);
    }
}
</style>

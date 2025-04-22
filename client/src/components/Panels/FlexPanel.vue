<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronLeft, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import DraggableSeparator from "@/components/Common/DraggableSeparator.vue";

library.add(faChevronLeft, faChevronRight);

const DEFAULT_WIDTH = 300;

interface Props {
    collapsible?: boolean;
    side?: "left" | "right";
    minWidth?: number;
    maxWidth?: number;
    reactiveWidth?: number;
}
const props = withDefaults(defineProps<Props>(), {
    collapsible: true,
    side: "right",
    minWidth: 200,
    maxWidth: 800,
    reactiveWidth: undefined,
});

const emit = defineEmits<{
    (e: "update:reactive-width", width: number): void;
}>();

const localPanelWidth = ref(DEFAULT_WIDTH);

const panelWidth = computed({
    get: () => {
        if (props.reactiveWidth !== undefined) {
            return props.reactiveWidth;
        }
        return localPanelWidth.value;
    },
    set: (width) => {
        if (props.reactiveWidth !== undefined) {
            emit("update:reactive-width", width);
        } else {
            localPanelWidth.value = width;
        }
    },
});

const root = ref<HTMLElement | null>(null);
const show = ref(true);

const showToggle = ref(false);
const hoverToggle = ref(false);

const isHoveringDragHandle = ref(false);
const isDragging = ref(false);

const hoverDraggableOrToggle = computed(() => (isHoveringDragHandle.value || hoverToggle.value) && !isDragging.value);

const toggleLinger = 500;
const toggleShowDelay = 600;
let showToggleTimeout: ReturnType<typeof setTimeout> | undefined;

watch(
    () => hoverDraggableOrToggle.value,
    (hover) => {
        clearTimeout(showToggleTimeout);

        if (hover) {
            showToggleTimeout = setTimeout(() => {
                showToggle.value = true;
            }, toggleShowDelay);
        } else {
            showToggleTimeout = setTimeout(() => {
                showToggle.value = false;
            }, toggleLinger);
        }
    }
);

const sideClasses = computed(() => ({
    left: props.side === "left",
    right: props.side === "right",
}));
</script>

<template>
    <div
        v-if="show"
        :id="side"
        ref="root"
        class="flex-panel"
        :class="{ ...sideClasses }"
        :style="`--width: ${panelWidth}px`">
        <DraggableSeparator
            :position="panelWidth"
            :side="props.side"
            :min="props.minWidth"
            :max="props.maxWidth"
            @positionChanged="(v) => (panelWidth = v)"
            @visibilityChanged="(v) => (isHoveringDragHandle = v)"></DraggableSeparator>

        <button
            v-if="props.collapsible"
            class="collapse-button open"
            :class="{ ...sideClasses, show: showToggle }"
            title="Close panel"
            @click="show = false"
            @mouseenter="hoverToggle = true"
            @focusin="hoverToggle = true"
            @mouseout="hoverToggle = false"
            @focusout="hoverToggle = false">
            <FontAwesomeIcon v-if="side === 'left'" fixed-width icon="fa-chevron-left" />
            <FontAwesomeIcon v-else icon="fa-chevron-right" fixed-width />
        </button>

        <slot />

        <div v-if="isDragging" class="interaction-overlay" />
    </div>
    <div v-else>
        <button
            class="collapse-button closed"
            :class="{ ...sideClasses, show: true }"
            title="Open panel"
            @click="
                show = true;
                hoverToggle = false;
            ">
            <FontAwesomeIcon v-if="side === 'right'" fixed-width icon="fa-chevron-left" />
            <FontAwesomeIcon v-else icon="fa-chevron-right" fixed-width />
        </button>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

$border-width: 6px;

.flex-panel {
    z-index: 100;
    flex-shrink: 0;
    display: flex;
    width: var(--width);
    position: relative;
    border-color: transparent;
    border-width: $border-width;
    box-shadow: 1px 0 transparent;
    transition: border-color 0.1s, box-shadow 0.1s;
    align-items: stretch;
    flex-direction: column;

    &::after {
        content: "";
        position: absolute;
        height: 100%;
        width: 1px;
        background-color: $border-color;
    }

    &.left {
        border-right-style: solid;

        &::after {
            right: -1px;
        }
    }

    &.right {
        border-left-style: solid;

        &::after {
            left: -1px;
        }
    }
}

.collapse-button {
    position: absolute;
    z-index: 100;

    --width: 0px;

    width: var(--width);
    overflow: hidden;

    transition: width 0.1s, left 0.1s, right 0.1s;
    border-style: none;

    &:hover,
    &.show,
    &:focus {
        --width: 1.5rem;
        border-style: solid;
    }

    height: 4rem;
    top: calc(50% - 2rem);
    padding: 0;
    display: grid;
    place-items: center;

    &.left {
        right: calc(var(--width) * -1);
        border-top-left-radius: 0;
        border-bottom-left-radius: 0;
    }

    &.right {
        left: calc(var(--width) * -1);
        border-top-right-radius: 0;
        border-bottom-right-radius: 0;
    }

    &.closed {
        --width: 0.75rem;
        border-style: solid;

        > * {
            transform: translateX(-0.15rem);
        }

        &:hover,
        &:focus {
            --width: 1.5rem;
        }

        &.right {
            left: unset;
            right: 0;
        }

        &.left {
            right: unset;
            left: 0;
        }
    }
}

.interaction-overlay {
    height: 100%;
    position: fixed;
    left: 0;
    width: 100%;
    cursor: ew-resize;
}
</style>

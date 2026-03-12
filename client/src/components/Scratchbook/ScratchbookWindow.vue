<script setup lang="ts">
import { computed, onBeforeUnmount } from "vue";

import { useWindowManagerStore, type WindowState } from "@/stores/windowManagerStore";

const props = defineProps<{
    window: WindowState;
}>();

const store = useWindowManagerStore();

const isFocused = computed(() => store.focusedId === props.window.id);

const windowStyle = computed(() => {
    if (props.window.maximized) {
        return {
            top: "0",
            left: "0",
            width: "100vw",
            height: "100vh",
            zIndex: props.window.zIndex,
        };
    }
    return {
        top: `calc(var(--masthead-height) + ${props.window.y}px)`,
        left: `${props.window.x}px`,
        width: `${props.window.width}px`,
        height: `${props.window.height}px`,
        zIndex: props.window.zIndex,
    };
});

const iframeSrc = computed(() => store.buildUrl(props.window.url));

// --- Drag ---
let dragStartMouseX = 0;
let dragStartMouseY = 0;
let dragStartX = 0;
let dragStartY = 0;

function onDragStart(e: MouseEvent) {
    if (props.window.maximized) {
        return;
    }
    e.preventDefault();
    store.focus(props.window.id);
    dragStartMouseX = e.clientX;
    dragStartMouseY = e.clientY;
    dragStartX = props.window.x;
    dragStartY = props.window.y;
    document.addEventListener("mousemove", onDragMove);
    document.addEventListener("mouseup", onDragEnd);
}

function onDragMove(e: MouseEvent) {
    store.updatePosition(
        props.window.id,
        dragStartX + (e.clientX - dragStartMouseX),
        dragStartY + (e.clientY - dragStartMouseY),
    );
}

function onDragEnd() {
    document.removeEventListener("mousemove", onDragMove);
    document.removeEventListener("mouseup", onDragEnd);
}

// --- Resize ---
const MIN_WIDTH = 200;
const MIN_HEIGHT = 120;
let resizeStartMouseX = 0;
let resizeStartMouseY = 0;
let resizeStartW = 0;
let resizeStartH = 0;

function onResizeStart(e: MouseEvent) {
    if (props.window.maximized) {
        return;
    }
    e.preventDefault();
    e.stopPropagation();
    store.focus(props.window.id);
    resizeStartMouseX = e.clientX;
    resizeStartMouseY = e.clientY;
    resizeStartW = props.window.width;
    resizeStartH = props.window.height;
    document.addEventListener("mousemove", onResizeMove);
    document.addEventListener("mouseup", onResizeEnd);
}

function onResizeMove(e: MouseEvent) {
    store.updateSize(
        props.window.id,
        Math.max(MIN_WIDTH, resizeStartW + (e.clientX - resizeStartMouseX)),
        Math.max(MIN_HEIGHT, resizeStartH + (e.clientY - resizeStartMouseY)),
    );
}

function onResizeEnd() {
    document.removeEventListener("mousemove", onResizeMove);
    document.removeEventListener("mouseup", onResizeEnd);
}

// --- Actions ---
function onFocus() {
    store.focus(props.window.id);
}

function onClose() {
    store.remove(props.window.id);
}

function onMaximize() {
    store.toggleMaximize(props.window.id);
}

onBeforeUnmount(() => {
    document.removeEventListener("mousemove", onDragMove);
    document.removeEventListener("mouseup", onDragEnd);
    document.removeEventListener("mousemove", onResizeMove);
    document.removeEventListener("mouseup", onResizeEnd);
});
</script>

<template>
    <div
        class="scratchbook-window"
        :class="{ focused: isFocused, maximized: window.maximized }"
        :style="windowStyle"
        @mousedown="onFocus">
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
        <div class="scratchbook-window-header" @mousedown.left="onDragStart">
            <span class="scratchbook-window-title">{{ window.title }}</span>
            <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
            <div class="scratchbook-window-controls" @mousedown.stop>
                <button class="scratchbook-window-btn" aria-label="Maximize" @click="onMaximize">
                    <span v-if="window.maximized">&#9724;</span>
                    <span v-else>&#9723;</span>
                </button>
                <button class="scratchbook-window-btn scratchbook-window-close" aria-label="Close" @click="onClose">
                    &#10005;
                </button>
            </div>
        </div>
        <div class="scratchbook-window-body">
            <iframe :src="iframeSrc" :title="window.title" />
            <div v-if="!isFocused" class="iframe-focus-overlay" @mousedown="onFocus" />
        </div>
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
        <div v-if="!window.maximized" class="scratchbook-resize-handle" @mousedown.left="onResizeStart" />
    </div>
</template>

<style scoped lang="scss">
.scratchbook-window {
    position: fixed;
    display: flex;
    flex-direction: column;
    border-radius: 0.5rem;
    box-shadow:
        0 0.25rem 0.5rem rgba(0, 0, 0, 0.08),
        0 0.75rem 1.5rem rgba(0, 0, 0, 0.12);
    background: var(--background-color);
    overflow: hidden;

    &.maximized {
        border-radius: 0;
        box-shadow: none;
    }
}

.scratchbook-window-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 2.25rem;
    padding: 0 0.5rem;
    border-bottom: 1px solid var(--color-grey-200);
    cursor: move;
    user-select: none;
}

.scratchbook-window-title {
    font-weight: 600;
    font-size: 0.875rem;
    color: var(--color-grey-900);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
}

.scratchbook-window-controls {
    display: flex;
    gap: 0.25rem;
    margin-left: 0.5rem;
}

.scratchbook-window-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    border: none;
    background: transparent;
    color: var(--color-grey-600);
    cursor: pointer;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    line-height: 1;
    padding: 0;

    &:hover {
        background: var(--color-grey-100);
        color: var(--color-grey-900);
    }

    &.scratchbook-window-close:hover {
        background: var(--color-red-100, #fee2e2);
        color: var(--color-red-600, #dc2626);
    }
}

.scratchbook-window-body {
    flex: 1;
    position: relative;
    overflow: hidden;

    iframe {
        width: 100%;
        height: 100%;
        border: none;
    }
}

.iframe-focus-overlay {
    position: absolute;
    inset: 0;
    z-index: 1;
}

.scratchbook-resize-handle {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 12px;
    height: 12px;
    cursor: nwse-resize;
}
</style>

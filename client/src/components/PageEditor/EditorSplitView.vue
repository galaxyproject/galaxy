<script setup lang="ts">
/**
 * Split layout with draggable resize handle.
 * Renders two slot-based panes side by side with configurable initial split.
 */
import { onBeforeUnmount, ref } from "vue";

withDefaults(
    defineProps<{
        initialSplit?: number;
    }>(),
    { initialSplit: 60 },
);

const splitPercent = ref(60);
const dragging = ref(false);
const containerRef = ref<HTMLElement>();

function startResize(e: MouseEvent) {
    e.preventDefault();
    dragging.value = true;
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", stopResize);
}

function onMouseMove(e: MouseEvent) {
    if (!dragging.value || !containerRef.value) {
        return;
    }
    const rect = containerRef.value.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = Math.round((x / rect.width) * 100);
    splitPercent.value = Math.max(20, Math.min(80, pct));
}

function stopResize() {
    dragging.value = false;
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", stopResize);
}

onBeforeUnmount(() => {
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", stopResize);
});
</script>

<template>
    <div
        ref="containerRef"
        class="editor-split-view"
        :class="{ 'is-dragging': dragging }"
        data-description="editor split view">
        <div class="split-pane editor-pane" :style="{ flexBasis: splitPercent + '%' }">
            <slot name="editor" />
        </div>
        <div class="split-handle" data-description="split resize handle" @mousedown="startResize">
            <div class="handle-bar" />
        </div>
        <div class="split-pane chat-pane" :style="{ flexBasis: 100 - splitPercent + '%' }">
            <slot name="chat" />
        </div>
    </div>
</template>

<style scoped>
.editor-split-view {
    display: flex;
    flex: 1;
    overflow: hidden;
    min-height: 0;
}

.editor-split-view.is-dragging {
    cursor: col-resize;
    user-select: none;
}

.split-pane {
    overflow: auto;
    min-width: 0;
}

.editor-pane {
    padding: 1rem;
}

.split-handle {
    flex-shrink: 0;
    width: 6px;
    cursor: col-resize;
    background: var(--border-color, #dee2e6);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.15s;
}

.split-handle:hover,
.is-dragging .split-handle {
    background: var(--brand-primary, #007bff);
}

.handle-bar {
    width: 2px;
    height: 24px;
    border-radius: 1px;
    background: rgba(255, 255, 255, 0.6);
}
</style>

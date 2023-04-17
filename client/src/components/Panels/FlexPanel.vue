<script setup>
import { computed, ref, watch } from "vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faChevronLeft, faChevronRight, faGripLinesVertical } from "@fortawesome/free-solid-svg-icons";
import { useDraggable } from "@vueuse/core";
import { LastQueue } from "utils/promise-queue";

const lastQueue = new LastQueue(10);

library.add({
    faChevronLeft,
    faChevronRight,
    faGripLinesVertical,
});

const props = defineProps({
    collapsible: {
        type: Boolean,
        default: true,
    },
    side: {
        type: String,
        default: "right",
    },
});

const draggable = ref();
const root = ref();
const rangeWidth = [200, 300, 600];
const panelWidth = ref(rangeWidth[1]);
const show = ref(true);

const { position, isDragging } = useDraggable(draggable, {
    preventDefault: true,
    exact: true,
});

watch(position, () => {
    lastQueue.enqueue(() => {
        const rectRoot = root.value.getBoundingClientRect();
        const rectDraggable = draggable.value.getBoundingClientRect();
        let newWidth = null;
        if (props.side === "right") {
            const offset = rectRoot.left - rectDraggable.left;
            newWidth = rectRoot.right - position.value.x - offset;
        } else {
            const offset = rectRoot.right - rectDraggable.left;
            newWidth = position.value.x - rectRoot.left + offset;
        }
        panelWidth.value = Math.max(rangeWidth[0], Math.min(rangeWidth[2], newWidth));
    });
});

const style = computed(() => {
    return show.value ? { width: `${panelWidth.value}px` } : null;
});

function toggle() {
    show.value = !show.value;
}
</script>

<template>
    <div v-if="show" ref="root" class="d-flex">
        <div class="d-flex flex-column" :style="style">
            <slot />
            <div v-if="side === 'right'" class="flex-panel-footer d-flex px-2 py-1">
                <div>
                    <font-awesome-icon icon="grip-lines-vertical" />
                    <div
                        ref="draggable"
                        class="interaction-area"
                        :class="{
                            'cursor-grab': !isDragging,
                            'cursor-grabbing': isDragging,
                        }" />
                </div>
                <div class="flex-fill" />
                <div v-if="collapsible" class="cursor-pointer">
                    <font-awesome-icon icon="chevron-right" />
                    <div class="interaction-area" @click="toggle" />
                </div>
            </div>
            <div v-else class="flex-panel-footer d-flex px-2 py-1">
                <div v-if="collapsible" class="cursor-pointer">
                    <font-awesome-icon icon="chevron-left" />
                    <div class="interaction-area" @click="toggle" />
                </div>
                <div class="flex-fill" />
                <div>
                    <font-awesome-icon icon="grip-lines-vertical" />
                    <div
                        ref="draggable"
                        class="interaction-area"
                        :class="{
                            'cursor-grab': !isDragging,
                            'cursor-grabbing': isDragging,
                        }" />
                </div>
            </div>
        </div>
        <div v-if="isDragging" class="interaction-overlay" />
    </div>
    <div v-else>
        <div v-if="side === 'right'" class="flex-panel-expand-right cursor-pointer px-2 py-1">
            <font-awesome-icon icon="chevron-left" />
            <div class="interaction-area" @click="toggle" />
        </div>
        <div v-else class="flex-panel-expand-left cursor-pointer px-2 py-1">
            <font-awesome-icon icon="chevron-right" />
            <div class="interaction-area" @click="toggle" />
        </div>
    </div>
</template>

<style>
@import "theme/blue.scss";
.cursor-grab {
    cursor: grab;
}
.cursor-grabbing {
    cursor: grabbing;
}
.flex-panel-expand {
    background: $panel-footer-bg-color;
    border: $border-default;
    bottom: 0;
    position: absolute;
    z-index: 1;
}
.flex-panel-expand-left {
    @extend .flex-panel-expand;
    border-top-right-radius: $border-radius-base;
    left: 0;
}
.flex-panel-expand-right {
    @extend .flex-panel-expand;
    border-top-left-radius: $border-radius-base;
    right: 0;
}
.flex-panel-footer {
    background: $panel-footer-bg-color;
}
.interaction-area {
    margin: -1.5rem;
    padding: 1.5rem;
    position: absolute;
    z-index: 2;
}
.interaction-overlay {
    height: 100%;
    position: fixed;
    left: 0;
    width: 100%;
}
</style>

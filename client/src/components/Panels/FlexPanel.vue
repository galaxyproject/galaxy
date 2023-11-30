<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronLeft, faChevronRight, faGripLinesVertical } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useDraggable } from "@vueuse/core";
import { computed, ref, watch } from "vue";

import { useTimeoutThrottle } from "@/composables/throttle";

import { determineWidth } from "./utilities";

const { throttle } = useTimeoutThrottle(10);

library.add(faChevronLeft, faChevronRight, faGripLinesVertical);

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

const minWidth = 200;
const maxWidth = 600;
const defaultWidth = 300;

const draggable = ref<HTMLElement | null>(null);
const root = ref<HTMLElement | null>(null);

const panelWidth = ref(defaultWidth);
const show = ref(true);

const { position, isDragging } = useDraggable(draggable, {
    preventDefault: true,
    exact: true,
});

const style = computed(() => {
    return show.value ? { width: `${panelWidth.value}px` } : {};
});

function toggle() {
    show.value = !show.value;
}

/** Watch position changes and adjust width accordingly */
watch(position, () => {
    throttle(() => {
        if (!root.value || !draggable.value) {
            return;
        }

        const rectRoot = root.value.getBoundingClientRect();
        const rectDraggable = draggable.value.getBoundingClientRect();
        panelWidth.value = determineWidth(rectRoot, rectDraggable, minWidth, maxWidth, props.side, position.value.x);
    });
});
</script>

<template>
    <div
        v-if="show"
        :id="side"
        ref="root"
        class="d-flex"
        :class="{ 'flex-panel-left': side === 'left', 'flex-panel-right': side === 'right' }">
        <div class="d-flex flex-column" :style="style">
            <slot />
            <div v-if="side === 'right'" class="flex-panel-footer d-flex px-2 py-1">
                <div id="right-drag">
                    <FontAwesomeIcon icon="grip-lines-vertical" />
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
                    <FontAwesomeIcon icon="chevron-right" />
                    <div id="right-collapse" class="interaction-area" @click="toggle" />
                </div>
            </div>
            <div v-else class="flex-panel-footer d-flex px-2 py-1">
                <div v-if="collapsible" class="cursor-pointer">
                    <FontAwesomeIcon icon="chevron-left" />
                    <div id="left-collapse" class="interaction-area" @click="toggle" />
                </div>
                <div class="flex-fill" />
                <div id="left-drag">
                    <FontAwesomeIcon icon="grip-lines-vertical" />
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
        <div v-if="side === 'right'" class="flex-panel-right-expand cursor-pointer px-2 py-1">
            <FontAwesomeIcon icon="chevron-left" />
            <div id="right-expand" class="interaction-area" @click="toggle" />
        </div>
        <div v-else class="flex-panel-left-expand cursor-pointer px-2 py-1">
            <FontAwesomeIcon icon="chevron-right" />
            <div id="left-expand" class="interaction-area" @click="toggle" />
        </div>
    </div>
</template>

<style scoped lang="scss">
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

.flex-panel-footer {
    background: $panel-footer-bg-color;
}

.flex-panel-left {
    border-right: $border-default;
}

.flex-panel-right {
    border-left: $border-default;
}

.flex-panel-left-expand {
    @extend .flex-panel-expand;
    border-top-right-radius: $border-radius-base;
    left: 0;
}

.flex-panel-right-expand {
    @extend .flex-panel-expand;
    border-top-left-radius: $border-radius-base;
    right: 0;
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

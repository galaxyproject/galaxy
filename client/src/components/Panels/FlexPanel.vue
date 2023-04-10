<script setup>
import { computed, ref, watch } from "vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faChevronLeft, faChevronRight, faGripLinesVertical } from "@fortawesome/free-solid-svg-icons";
import { useDraggable } from "@vueuse/core";

library.add({
    faChevronLeft,
    faChevronRight,
    faGripLinesVertical,
});

const draggable = ref();
const rangeWidth = [200, 300, 600];
const panelWidth = ref(rangeWidth[1]);
const show = ref(true);

const { position, isDragging } = useDraggable(draggable, {
    preventDefault: true,
    exact: true,
});

watch(position, () => {
    const newWidth = window.innerWidth - position.value.x;
    panelWidth.value = Math.max(rangeWidth[0], Math.min(rangeWidth[2], newWidth));
});

const style = computed(() => {
    return show.value ? { width: `${panelWidth.value}px` } : null;
});

function toggle() {
    show.value = !show.value;
}
</script>

<template>
    <div class="d-flex">
        <div class="d-flex flex-column" :style="style">
            <slot v-if="show" />
            <div v-else class="flex-fill" />
            <div class="flex-panel-footer d-flex px-2 p-1" :class="{ 'flex-panel-border': !show }">
                <font-awesome-icon
                    v-if="show"
                    ref="draggable"
                    icon="grip-lines-vertical"
                    :class="{
                        'cursor-grab': !isDragging,
                        'cursor-grabbing': isDragging,
                    }" />
                <div class="flex-fill" />
                <font-awesome-icon v-if="show" class="cursor-pointer" icon="chevron-right" @click="toggle" />
                <font-awesome-icon v-else class="cursor-pointer" icon="chevron-left" @click="toggle" />
            </div>
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
.flex-panel-footer {
    background: $panel-footer-bg-color;
}
.flex-panel-border {
    border: $border-default;
    border-top-left-radius: $border-radius-base;
}
</style>

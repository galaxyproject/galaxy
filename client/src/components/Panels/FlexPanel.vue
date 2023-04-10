<script setup>
import { ref } from "vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faChevronLeft, faChevronRight, faGripLinesVertical } from "@fortawesome/free-solid-svg-icons";

library.add({
    faChevronLeft,
    faChevronRight,
    faGripLinesVertical,
});

const show = ref(true);
const dragging = ref(false);

function toggle() {
    show.value = !show.value;
}
</script>

<template>
    <div class="d-flex">
        <div class="d-flex flex-column" :class="{ 'flex-panel-column': show }">
            <slot v-if="show" />
            <div v-else class="flex-fill" />
            <div class="flex-panel-footer d-flex px-2 p-1" :class="{ 'flex-panel-border': !show }" @click="toggle">
                <font-awesome-icon v-if="show" icon="grip-lines-vertical" class="flex-panel-grab" />
                <div class="flex-fill" />
                <font-awesome-icon v-if="show" icon="chevron-right" />
                <font-awesome-icon v-else icon="chevron-left" />
            </div>
        </div>
    </div>
</template>

<style>
@import "theme/blue.scss";
.flex-panel-grab {
    cursor: grab;
}
.flex-panel-column {
    width: 18rem;
}
.flex-panel-footer {
    background: $panel-footer-bg-color;
    cursor: pointer;
}
.flex-panel-border {
    border: $border-default;
    border-top-left-radius: $border-radius-base;
}
</style>

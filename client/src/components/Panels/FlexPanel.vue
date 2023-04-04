<script setup>
import { ref } from "vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faChevronLeft, faChevronRight } from "@fortawesome/free-solid-svg-icons";

library.add({
    faChevronLeft,
    faChevronRight,
});

const show = ref(true);

function toggle() {
    show.value = !show.value;
}
</script>

<template>
    <div class="d-flex">
        <div class="d-flex flex-column">
            <slot v-if="show" />
            <div v-else class="flex-fill" />
            <div class="flex-panel-footer d-flex px-2 p-1" :class="{ 'flex-panel-border': !show }" @click="toggle">
                <div class="flex-fill" />
                <icon v-if="show" class="align-self-end" icon="chevron-right" />
                <icon v-else icon="chevron-left" />
            </div>
        </div>
    </div>
</template>

<style>
@import "theme/blue.scss";
.flex-panel-footer {
    background: $panel-footer-bg-color;
    cursor: pointer;
}
.flex-panel-border {
    border: $border-default;
    border-top-left-radius: $border-radius-base;
}
</style>

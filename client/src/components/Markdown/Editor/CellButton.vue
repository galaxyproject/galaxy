<template>
    <BButton
        v-b-tooltip.noninteractive.bottom
        class="border-0 m-1 px-1 py-0"
        :class="{ active, 'cell-button-hide': !show }"
        :title="title"
        :variant="active ? 'outline-secondary' : 'outline-primary'"
        @click="$emit('click')"
        @mouseleave="onMouseLeave($event)">
        <FontAwesomeIcon :icon="icon" fixed-width />
    </BButton>
</template>

<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, VBTooltipPlugin } from "bootstrap-vue";
import type { IconDefinition } from "font-awesome-6";
import Vue from "vue";

Vue.use(VBTooltipPlugin);

withDefaults(
    defineProps<{
        active?: boolean;
        icon: IconDefinition,
        show?: boolean;
        title: string;
    }>(),
    {
        active: false,
        show: true,
    }
);

defineEmits<{
    (e: "click"): void;
}>();

function onMouseLeave(event: Event) {
    const target = event.target as HTMLElement;
    target.blur();
}
</script>

<style>
.cell-button-hide {
    color: transparent !important;
}
</style>
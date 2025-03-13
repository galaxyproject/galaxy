<template>
    <BButton
        v-b-tooltip.right
        class="border-0 m-1 px-1 py-0"
        :class="{ active, 'cell-button-hide': !show }"
        :title="title"
        :variant="active ? 'outline-secondary' : 'outline-primary'"
        @click="$emit('click')"
        @mouseleave="onMouseLeave($event)">
        <slot />
    </BButton>
</template>

<script setup lang="ts">
import { BButton, VBTooltipPlugin } from "bootstrap-vue";
import Vue from "vue";

Vue.use(VBTooltipPlugin);

withDefaults(
    defineProps<{
        active?: boolean;
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

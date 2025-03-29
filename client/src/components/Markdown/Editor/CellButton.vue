<template>
    <BButton
        v-b-tooltip.noninteractive="tooltipOptions"
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
import Vue, { computed } from "vue";

Vue.use(VBTooltipPlugin);

const props = withDefaults(
    defineProps<{
        active?: boolean;
        icon: IconDefinition;
        show?: boolean;
        title: string;
        tooltipPlacement?: "top" | "right" | "bottom" | "left";
    }>(),
    {
        active: false,
        show: true,
        tooltipPlacement: "right",
    }
);

defineEmits<{
    (e: "click"): void;
}>();

const tooltipOptions = computed(() => ({
    placement: props.tooltipPlacement,
}));

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

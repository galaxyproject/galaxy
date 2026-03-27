<script setup lang="ts">
/**
 * Button-style dropdown item (no link behavior).
 * Replaces BDropdownItemButton from bootstrap-vue.
 */

import { computed, inject } from "vue";

const props = withDefaults(
    defineProps<{
        active?: boolean;
        disabled?: boolean;
        variant?: string;
    }>(),
    {
        active: false,
        disabled: false,
        variant: undefined,
    },
);

const emit = defineEmits<{
    (e: "click", event: MouseEvent): void;
}>();

const hideDropdown = inject<() => void>("g-dropdown-hide", () => {});

const classes = computed(() => ({
    "dropdown-item": true,
    active: props.active,
    disabled: props.disabled,
    [`text-${props.variant}`]: !!props.variant,
}));

function onClick(event: MouseEvent) {
    if (props.disabled) {
        return;
    }
    emit("click", event);
    hideDropdown();
}
</script>

<template>
    <button type="button" :class="classes" :disabled="disabled" role="menuitem" @click="onClick">
        <slot />
    </button>
</template>

<style scoped>
.dropdown-item {
    cursor: pointer;
}
</style>

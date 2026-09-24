<script setup lang="ts">
/** Replaces BDropdownItem. Always an <a>, since Selenium finds items by link text and "a.dropdown-item". */

import { computed, inject } from "vue";

import { dropdownHideKey } from "./dropdownContext";

const props = withDefaults(
    defineProps<{
        /** Router link destination */
        to?: string | object;
        /** External link URL */
        href?: string;
        /** Link target (_blank, etc.) */
        target?: string;
        /** Active state */
        active?: boolean;
        /** Disabled state */
        disabled?: boolean;
        /** Color variant */
        variant?: string;
        /** Title/tooltip text */
        title?: string;
    }>(),
    {
        to: undefined,
        href: undefined,
        target: undefined,
        active: false,
        disabled: false,
        variant: undefined,
        title: undefined,
    },
);

const emit = defineEmits<{
    (e: "click", event: MouseEvent): void;
}>();

const hideDropdown = inject(dropdownHideKey, () => {});

const classes = computed(() => ({
    "dropdown-item": true,
    active: props.active,
    disabled: props.disabled,
    [`text-${props.variant}`]: !!props.variant,
}));

function onClick(event: MouseEvent) {
    if (props.disabled) {
        event.preventDefault();
        return;
    }
    // Only "#" action items cancel navigation: a real href must open, target="_blank" included
    if (!props.to && (!props.href || props.href === "#")) {
        event.preventDefault();
    }
    emit("click", event);
    hideDropdown();
}
</script>

<template>
    <!-- A disabled item is a plain anchor: RouterLink navigates before any click handler here could cancel it -->
    <router-link
        v-if="to && !disabled"
        :class="classes"
        :to="to"
        :target="target"
        :title="title"
        :aria-current="active ? 'true' : undefined"
        role="menuitem"
        tabindex="-1"
        @click.native="onClick">
        <slot />
    </router-link>
    <a
        v-else
        :class="classes"
        :href="!disabled && href ? href : '#'"
        :target="target"
        :title="title"
        :aria-disabled="disabled || undefined"
        :aria-current="active ? 'true' : undefined"
        role="menuitem"
        tabindex="-1"
        @click="onClick">
        <slot />
    </a>
</template>

<style scoped>
.dropdown-item {
    cursor: pointer;
}

/* Focus shares the hover background: the light ring tells them apart, the blue edge shows on unfilled active items */
.dropdown-item:focus-visible {
    outline: 2px solid var(--color-grey-100);
    outline-offset: -4px;
    box-shadow: inset 0 0 0 2px var(--color-blue-600);
}
</style>
